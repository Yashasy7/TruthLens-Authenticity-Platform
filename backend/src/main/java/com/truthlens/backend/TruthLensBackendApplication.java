package com.truthlens.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * TruthLens Backend — Main Application Entry Point.
 *
 * <p>TruthLens is an Intelligent Multimedia Authenticity Verification Platform
 * operating in the Cyber Security domain. This class bootstraps the central
 * Spring Boot backend service.</p>
 *
 * <p>Module: Module 01 — Authentication, RBAC &amp; User Management will be
 * implemented incrementally in subsequent stages.</p>
 */
@SpringBootApplication
public class TruthLensBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(TruthLensBackendApplication.class, args);
    }
}
