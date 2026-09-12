package com.truthlens.backend.service;

import com.truthlens.backend.dto.UpdateProfileRequest;
import com.truthlens.backend.dto.UserProfileResponse;
import com.truthlens.backend.entity.AccountStatus;
import com.truthlens.backend.entity.Role;
import com.truthlens.backend.entity.RoleName;
import com.truthlens.backend.entity.User;
import com.truthlens.backend.exception.UserNotFoundException;
import com.truthlens.backend.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("UserService — unit tests")
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    private UserService userService;

    private User sampleUser;
    private UUID sampleUserId;
    private OffsetDateTime initialCreatedAt;
    private OffsetDateTime initialUpdatedAt;

    @BeforeEach
    void setUp() {
        userService = new UserService(userRepository);

        sampleUserId = UUID.randomUUID();
        initialCreatedAt = OffsetDateTime.now().minusHours(2);
        initialUpdatedAt = initialCreatedAt;

        sampleUser = new User("alice@truthlens.io", "hashedPassword123", "Alice Smith");
        sampleUser.setStatus(AccountStatus.ACTIVE);
        sampleUser.getRoles().add(new Role(RoleName.USER, "Standard user role"));

        try {
            Field idField = User.class.getDeclaredField("id");
            idField.setAccessible(true);
            idField.set(sampleUser, sampleUserId);

            Field createdAtField = User.class.getDeclaredField("created_at".equals(idField.getName()) ? "created_at" : "createdAt");
            createdAtField.setAccessible(true);
            createdAtField.set(sampleUser, initialCreatedAt);

            Field updatedAtField = User.class.getDeclaredField("updatedAt");
            updatedAtField.setAccessible(true);
            updatedAtField.set(sampleUser, initialUpdatedAt);
        } catch (Exception e) {
            throw new RuntimeException("Failed to set reflection fields on test User", e);
        }
    }

    @Test
    @DisplayName("getProfile — returns safe profile for existing user")
    void getProfile_success() {
        when(userRepository.findByEmail("alice@truthlens.io")).thenReturn(Optional.of(sampleUser));

        UserProfileResponse response = userService.getProfile("alice@truthlens.io");

        assertThat(response).isNotNull();
        assertThat(response.getId()).isEqualTo(sampleUserId);
        assertThat(response.getEmail()).isEqualTo("alice@truthlens.io");
        assertThat(response.getFullName()).isEqualTo("Alice Smith");
        assertThat(response.getStatus()).isEqualTo("ACTIVE");
        assertThat(response.getRoles()).containsExactly("USER");
        assertThat(response.getCreatedAt()).isEqualTo(initialCreatedAt);
        assertThat(response.getUpdatedAt()).isEqualTo(initialUpdatedAt);
    }

    @Test
    @DisplayName("getProfile — throws UserNotFoundException when user does not exist")
    void getProfile_userNotFound() {
        when(userRepository.findByEmail("nonexistent@truthlens.io")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.getProfile("nonexistent@truthlens.io"))
                .isInstanceOf(UserNotFoundException.class)
                .hasMessageContaining("nonexistent@truthlens.io");
    }

    @Test
    @DisplayName("updateProfile — updates fullName, persists entity, and refreshes updatedAt")
    void updateProfile_success() {
        when(userRepository.findByEmail("alice@truthlens.io")).thenReturn(Optional.of(sampleUser));
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> {
            User u = invocation.getArgument(0);
            Method onUpdate = User.class.getDeclaredMethod("onUpdate");
            onUpdate.setAccessible(true);
            onUpdate.invoke(u);
            return u;
        });

        UpdateProfileRequest request = new UpdateProfileRequest("Alice Johnson");
        UserProfileResponse response = userService.updateProfile("alice@truthlens.io", request);

        assertThat(response).isNotNull();
        assertThat(response.getFullName()).isEqualTo("Alice Johnson");
        assertThat(response.getCreatedAt()).isEqualTo(initialCreatedAt);
        assertThat(response.getUpdatedAt()).isAfter(initialUpdatedAt);

        verify(userRepository).save(sampleUser);
        assertThat(sampleUser.getFullName()).isEqualTo("Alice Johnson");
    }

    @Test
    @DisplayName("updateProfile — throws UserNotFoundException when user does not exist")
    void updateProfile_userNotFound() {
        when(userRepository.findByEmail("nonexistent@truthlens.io")).thenReturn(Optional.empty());

        UpdateProfileRequest request = new UpdateProfileRequest("New Name");

        assertThatThrownBy(() -> userService.updateProfile("nonexistent@truthlens.io", request))
                .isInstanceOf(UserNotFoundException.class)
                .hasMessageContaining("nonexistent@truthlens.io");
    }

    @Test
    @DisplayName("updateProfile — protected fields remain untouched")
    void updateProfile_protectedFieldsRemainUnchanged() {
        when(userRepository.findByEmail("alice@truthlens.io")).thenReturn(Optional.of(sampleUser));
        when(userRepository.save(any(User.class))).thenReturn(sampleUser);

        UpdateProfileRequest request = new UpdateProfileRequest("Updated Name");
        UserProfileResponse response = userService.updateProfile("alice@truthlens.io", request);

        assertThat(response.getId()).isEqualTo(sampleUserId);
        assertThat(response.getEmail()).isEqualTo("alice@truthlens.io");
        assertThat(response.getStatus()).isEqualTo("ACTIVE");
        assertThat(response.getRoles()).containsExactly("USER");
        assertThat(response.getCreatedAt()).isEqualTo(initialCreatedAt);
        assertThat(sampleUser.getPasswordHash()).isEqualTo("hashedPassword123");
    }
}
