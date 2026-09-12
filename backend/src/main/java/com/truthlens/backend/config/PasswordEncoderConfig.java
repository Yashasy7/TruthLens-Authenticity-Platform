package com.truthlens.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Configuration class that exposes the {@link PasswordEncoder} bean.
 *
 * <p>BCrypt is the recommended password hashing algorithm for web applications:
 * it is adaptive (cost factor adjustable), includes a built-in salt, and is
 * resistant to GPU-accelerated brute-force attacks.</p>
 *
 * <p>The default BCrypt strength (cost factor 10) is used. This provides a
 * good balance between security and performance for typical web workloads.
 * The cost factor can be raised in a later operational stage without breaking
 * existing stored hashes.</p>
 *
 * <p>Kept in a separate configuration class (rather than inlined into
 * {@code SecurityConfig}) so that the {@code PasswordEncoder} bean can be
 * injected by {@code AuthService} without creating a circular dependency
 * with Spring Security's authentication infrastructure.</p>
 */
@Configuration
public class PasswordEncoderConfig {

    /**
     * Exposes a BCrypt {@link PasswordEncoder} as a Spring bean.
     *
     * <p>BCrypt strength defaults to 10. All passwords stored in the
     * {@code users.password_hash} column are produced by this encoder.</p>
     *
     * @return the {@link BCryptPasswordEncoder} instance
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
