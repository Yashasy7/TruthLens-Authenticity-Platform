package com.truthlens.backend.service;

import com.truthlens.backend.dto.AuthResponse;
import com.truthlens.backend.dto.LoginRequest;
import com.truthlens.backend.dto.RegisterRequest;
import com.truthlens.backend.entity.AccountStatus;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.AccountSuspendedException;
import com.truthlens.backend.exception.EmailAlreadyExistsException;
import com.truthlens.backend.exception.InvalidCredentialsException;
import com.truthlens.backend.repository.RoleRepository;
import com.truthlens.backend.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link AuthService}.
 *
 * <p>Uses Mockito to isolate the service from the database layer.
 * A real {@link BCryptPasswordEncoder} with cost 4 is used to keep tests
 * fast while still exercising actual hashing behaviour.</p>
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("AuthService — unit tests")
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private RoleRepository roleRepository;

    // Use a real BCrypt encoder at cost 4 — fast in tests, real behaviour.
    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder(4);

    private AuthService authService;

    @BeforeEach
    void setUp() {
        authService = new AuthService(userRepository, roleRepository, passwordEncoder);
    }

    // =========================================================================
    // Registration tests
    // =========================================================================

    @Test
    @DisplayName("register — successful registration creates user with USER role and BCrypt hash")
    void register_success() {
        // Arrange
        RegisterRequest request = new RegisterRequest(
                "Alice@Example.COM", "securePass1", "Alice Example");

        Role userRole = new Role(RoleName.USER, "Standard user");

        when(userRepository.existsByEmail("alice@example.com")).thenReturn(false);
        when(roleRepository.findByName(RoleName.USER)).thenReturn(Optional.of(userRole));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        // Act
        AuthResponse response = authService.register(request);

        // Assert — response is safe (no password data)
        assertThat(response.getMessage()).isEqualTo("Registration successful");
        assertThat(response.getEmail()).isEqualTo("alice@example.com"); // normalised
        assertThat(response.getFullName()).isEqualTo("Alice Example");
        assertThat(response.getStatus()).isEqualTo("ACTIVE");
        assertThat(response.getRoles()).containsExactly("USER");

        // Verify the saved entity has a BCrypt hash, NOT the plaintext password
        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(userCaptor.capture());
        User saved = userCaptor.getValue();

        assertThat(saved.getPasswordHash()).isNotEqualTo("securePass1");
        assertThat(saved.getPasswordHash()).startsWith("$2a$");
        assertThat(passwordEncoder.matches("securePass1", saved.getPasswordHash())).isTrue();
        assertThat(saved.getStatus()).isEqualTo(AccountStatus.ACTIVE);
        assertThat(saved.getRoles()).containsExactly(userRole);
    }

    @Test
    @DisplayName("register — email is normalised (trimmed and lowercased) before persistence")
    void register_emailNormalisation() {
        RegisterRequest request = new RegisterRequest(
                "  USER@EXAMPLE.COM  ", "password1", null);
        Role userRole = new Role(RoleName.USER, "Standard user");

        when(userRepository.existsByEmail("user@example.com")).thenReturn(false);
        when(roleRepository.findByName(RoleName.USER)).thenReturn(Optional.of(userRole));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        AuthResponse response = authService.register(request);

        assertThat(response.getEmail()).isEqualTo("user@example.com");

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        assertThat(captor.getValue().getEmail()).isEqualTo("user@example.com");
    }

    @Test
    @DisplayName("register — duplicate email throws EmailAlreadyExistsException (HTTP 409)")
    void register_duplicateEmail_throwsConflict() {
        RegisterRequest request = new RegisterRequest(
                "existing@example.com", "password1", null);

        when(userRepository.existsByEmail("existing@example.com")).thenReturn(true);

        assertThatThrownBy(() -> authService.register(request))
                .isInstanceOf(EmailAlreadyExistsException.class)
                .hasMessageContaining("existing@example.com");

        // User must never be saved on a duplicate email
        verify(userRepository, never()).save(any());
    }

    @Test
    @DisplayName("register — password is stored as BCrypt hash, never plaintext")
    void register_passwordStoredAsBCryptHash() {
        RegisterRequest request = new RegisterRequest(
                "test@example.com", "myS3cretPass", "Test User");
        Role userRole = new Role(RoleName.USER, "Standard user");

        when(userRepository.existsByEmail(anyString())).thenReturn(false);
        when(roleRepository.findByName(RoleName.USER)).thenReturn(Optional.of(userRole));
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        authService.register(request);

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());

        String storedHash = captor.getValue().getPasswordHash();

        // Must be a valid BCrypt hash
        assertThat(storedHash).startsWith("$2a$");
        // Must NOT be the plaintext
        assertThat(storedHash).isNotEqualTo("myS3cretPass");
        // Must match the original password via the encoder
        assertThat(passwordEncoder.matches("myS3cretPass", storedHash)).isTrue();
        // A different password must NOT match
        assertThat(passwordEncoder.matches("wrongPassword", storedHash)).isFalse();
    }

    // =========================================================================
    // Login tests
    // =========================================================================

    @Test
    @DisplayName("login — successful login with correct password returns AuthResponse")
    void login_success() {
        String rawPassword = "correctPassword9";
        String hash = passwordEncoder.encode(rawPassword);

        User user = new User("bob@example.com", hash, "Bob");
        user.setStatus(AccountStatus.ACTIVE);
        Role userRole = new Role(RoleName.USER, "Standard user");
        user.getRoles().add(userRole);

        when(userRepository.findByEmail("bob@example.com"))
                .thenReturn(Optional.of(user));

        LoginRequest request = new LoginRequest("bob@example.com", rawPassword);
        AuthResponse response = authService.login(request);

        assertThat(response.getMessage()).isEqualTo("Login successful");
        assertThat(response.getEmail()).isEqualTo("bob@example.com");
        assertThat(response.getStatus()).isEqualTo("ACTIVE");
        assertThat(response.getRoles()).containsExactly("USER");
    }

    @Test
    @DisplayName("login — email not found throws InvalidCredentialsException (HTTP 401)")
    void login_emailNotFound_throwsUnauthorized() {
        when(userRepository.findByEmail(anyString())).thenReturn(Optional.empty());

        LoginRequest request = new LoginRequest("nobody@example.com", "password1");

        assertThatThrownBy(() -> authService.login(request))
                .isInstanceOf(InvalidCredentialsException.class)
                .hasMessage("Invalid email or password.");
    }

    @Test
    @DisplayName("login — wrong password throws InvalidCredentialsException (HTTP 401)")
    void login_wrongPassword_throwsUnauthorized() {
        String hash = passwordEncoder.encode("correctPassword9");
        User user = new User("carol@example.com", hash, "Carol");
        user.setStatus(AccountStatus.ACTIVE);

        when(userRepository.findByEmail("carol@example.com"))
                .thenReturn(Optional.of(user));

        LoginRequest request = new LoginRequest("carol@example.com", "wrongPassword");

        assertThatThrownBy(() -> authService.login(request))
                .isInstanceOf(InvalidCredentialsException.class)
                .hasMessage("Invalid email or password.");
    }

    @Test
    @DisplayName("login — suspended account throws AccountSuspendedException (HTTP 403)")
    void login_suspendedAccount_throwsForbidden() {
        String hash = passwordEncoder.encode("password123");
        User user = new User("dave@example.com", hash, "Dave");
        user.setStatus(AccountStatus.SUSPENDED);

        when(userRepository.findByEmail("dave@example.com"))
                .thenReturn(Optional.of(user));

        LoginRequest request = new LoginRequest("dave@example.com", "password123");

        assertThatThrownBy(() -> authService.login(request))
                .isInstanceOf(AccountSuspendedException.class);
    }

    @Test
    @DisplayName("login — email normalised (trimmed + lowercased) before lookup")
    void login_emailNormalisation() {
        String hash = passwordEncoder.encode("password123");
        User user = new User("eve@example.com", hash, "Eve");
        user.setStatus(AccountStatus.ACTIVE);
        user.getRoles().add(new Role(RoleName.USER, "Standard user"));

        // Service normalises to lowercase before calling the repository
        when(userRepository.findByEmail("eve@example.com"))
                .thenReturn(Optional.of(user));

        LoginRequest request = new LoginRequest("  EVE@EXAMPLE.COM  ", "password123");
        AuthResponse response = authService.login(request);

        assertThat(response.getEmail()).isEqualTo("eve@example.com");
        verify(userRepository).findByEmail("eve@example.com");
    }

    @Test
    @DisplayName("login — PENDING_VERIFICATION account can log in (status check only rejects SUSPENDED)")
    void login_pendingVerification_allowed() {
        String hash = passwordEncoder.encode("password123");
        User user = new User("frank@example.com", hash, "Frank");
        user.setStatus(AccountStatus.PENDING_VERIFICATION);
        user.getRoles().add(new Role(RoleName.USER, "Standard user"));

        when(userRepository.findByEmail("frank@example.com"))
                .thenReturn(Optional.of(user));

        LoginRequest request = new LoginRequest("frank@example.com", "password123");
        AuthResponse response = authService.login(request);

        assertThat(response.getStatus()).isEqualTo("PENDING_VERIFICATION");
    }
}
