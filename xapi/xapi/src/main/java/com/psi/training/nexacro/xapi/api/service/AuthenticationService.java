package com.psi.training.nexacro.xapi.api.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.psi.training.nexacro.xapi.common.ApiException;
import com.psi.training.nexacro.xapi.common.NexacroProtocol;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthenticationService {
    private static final int PBKDF2_ITERATIONS = 210_000;
    private static final int HASH_BITS = 256;
    private final JdbcTemplate jdbc;
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthenticationService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public Map<String, Object> register(JsonNode payload) {
        Map<String, Object> input = NexacroProtocol.firstRow(payload, "dsSignup");
        String name = NexacroProtocol.value(input, "Name");
        String email = normalizeEmail(NexacroProtocol.value(input, "Email"));
        String password = NexacroProtocol.rawValue(input, "Password");
        name = name.trim();
        validateCredentials(name, email, password);
        if (jdbc.queryForObject("SELECT COUNT(*) FROM app_user WHERE email = ?", Integer.class, email) > 0) {
            throw new ApiException("An account with this email already exists.");
        }
        try {
            jdbc.update("INSERT INTO app_user (full_name, email, password_hash) VALUES (?, ?, ?)",
                name, email, hashPassword(password));
        } catch (DuplicateKeyException duplicate) {
            throw new ApiException("An account with this email already exists.");
        }
        long userId = jdbc.queryForObject("SELECT user_id FROM app_user WHERE email = ?", Long.class, email);
        return newSession(userId, name, email, false);
    }

    @Transactional
    public Map<String, Object> login(JsonNode payload) {
        Map<String, Object> input = NexacroProtocol.firstRow(payload, "dsLogin");
        String email = normalizeEmail(NexacroProtocol.value(input, "Email"));
        String password = NexacroProtocol.rawValue(input, "Password");
        if (email.isBlank() || password.isBlank()) throw new ApiException("Email and password are required.");
        var users = jdbc.query(
            "SELECT user_id, full_name, password_hash FROM app_user WHERE email = ?",
            (rs, row) -> new User(rs.getLong("user_id"), rs.getString("full_name"), rs.getString("password_hash")),
            email);
        if (users.isEmpty() || !verifyPassword(password, users.get(0).passwordHash())) {
            throw new ApiException("Email or password is incorrect.");
        }
        String remember = NexacroProtocol.value(input, "RememberMe");
        return newSession(users.get(0).id(), users.get(0).name(), email,
            "true".equalsIgnoreCase(remember) || "1".equals(remember));
    }

    public long requireSession(JsonNode payload) {
        return requireSession(NexacroProtocol.parameter(payload, "sessionToken"));
    }

    public long requireSession(String token) {
        if (token == null || token.isBlank()) throw new ApiException("Your session has expired. Sign in again.");
        var ids = jdbc.query(
            "SELECT user_id FROM user_session WHERE token_hash = ? AND expires_at > ?",
            (rs, row) -> rs.getLong(1), sha256(token), Timestamp.from(Instant.now()));
        if (ids.isEmpty()) throw new ApiException("Your session has expired. Sign in again.");
        return ids.get(0);
    }

    @Transactional
    public void revokeSession(JsonNode payload) {
        String token = NexacroProtocol.parameter(payload, "sessionToken");
        if (token.isBlank()) {
            token = NexacroProtocol.value(NexacroProtocol.firstRow(payload, "dsLogout"), "SessionToken");
        }
        long userId = requireSession(token);
        jdbc.update("DELETE FROM user_session WHERE user_id = ? AND token_hash = ?", userId, sha256(token));
    }

    private Map<String, Object> newSession(long userId, String name, String email, boolean remember) {
        byte[] tokenBytes = new byte[32];
        secureRandom.nextBytes(tokenBytes);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(tokenBytes);
        Instant expiry = Instant.now().plus(remember ? Duration.ofDays(30) : Duration.ofHours(8));
        jdbc.update("INSERT INTO user_session (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            userId, sha256(token), Timestamp.from(expiry));
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("UserID", String.valueOf(userId));
        row.put("Name", name);
        row.put("Email", email);
        row.put("Token", token);
        row.put("ExpiresAt", expiry.toString());
        row.put("RememberMe", remember ? "1" : "0");
        return row;
    }

    private void validateCredentials(String name, String email, String password) {
        name = name.trim();
        if (name.isBlank()) throw new ApiException("Name is required.");
        if (!email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) throw new ApiException("Enter a valid email address.");
        if (password.length() < 8) throw new ApiException("Password must have at least 8 characters.");
    }

    private String normalizeEmail(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private String hashPassword(String password) {
        byte[] salt = new byte[16];
        secureRandom.nextBytes(salt);
        byte[] hash = derive(password, salt, PBKDF2_ITERATIONS);
        return "pbkdf2$" + PBKDF2_ITERATIONS + "$"
            + Base64.getUrlEncoder().withoutPadding().encodeToString(salt) + "$"
            + Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
    }

    private boolean verifyPassword(String password, String encoded) {
        try {
            String[] pieces = encoded.split("\\$");
            if (pieces.length != 4 || !"pbkdf2".equals(pieces[0])) return false;
            int iterations = Integer.parseInt(pieces[1]);
            byte[] salt = Base64.getUrlDecoder().decode(pieces[2]);
            byte[] expected = Base64.getUrlDecoder().decode(pieces[3]);
            return MessageDigest.isEqual(expected, derive(password, salt, iterations));
        } catch (RuntimeException exception) {
            return false;
        }
    }

    private byte[] derive(String password, byte[] salt, int iterations) {
        PBEKeySpec spec = new PBEKeySpec(password.toCharArray(), salt, iterations, HASH_BITS);
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();
        } catch (Exception exception) {
            throw new IllegalStateException("Password hashing is unavailable.", exception);
        } finally {
            spec.clearPassword();
        }
    }

    private String sha256(String value) {
        try {
            byte[] bytes = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        } catch (Exception exception) {
            throw new IllegalStateException("Session hashing is unavailable.", exception);
        }
    }

    private record User(long id, String name, String passwordHash) {}
}
