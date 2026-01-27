package com.example.usermanagement;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * User Management Module
 * ユーザー情報の管理を行うモジュール
 */
public class UserManagement {

    /** メールアドレスのバリデーションパターン */
    private static final Pattern EMAIL_PATTERN =
        Pattern.compile("^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$");

    /** メールアドレスのバリデーション */
    public static boolean validateEmail(String email) {
        return email != null && EMAIL_PATTERN.matcher(email).matches();
    }

    /** 年齢のバリデーション（0-150の範囲） */
    public static boolean validateAge(int age) {
        return age >= 0 && age <= 150;
    }

    /** ユーザー情報を表すクラス */
    public static class User {
        private int userId;
        private String name;
        private String email;
        private int age;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public User(int userId, String name, String email, int age) {
            this.userId = userId;
            this.name = name;
            this.email = email;
            this.age = age;
            this.createdAt = LocalDateTime.now();
            this.updatedAt = LocalDateTime.now();
        }

        public int getUserId() { return userId; }
        public void setUserId(int userId) { this.userId = userId; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public int getAge() { return age; }
        public void setAge(int age) { this.age = age; }
        public LocalDateTime getCreatedAt() { return createdAt; }
        public LocalDateTime getUpdatedAt() { return updatedAt; }
        public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }

        @Override
        public String toString() {
            return String.format("User(id=%d, name=%s, email=%s)", userId, name, email);
        }
    }

    /** ユーザーデータの永続化を担当するリポジトリ */
    public static class UserRepository {
        private final Map<Integer, User> users = new HashMap<>();
        private int nextId = 1;

        public User save(User user) {
            if (user.getUserId() == 0) {
                user.setUserId(nextId++);
            }
            user.setUpdatedAt(LocalDateTime.now());
            users.put(user.getUserId(), user);
            return user;
        }

        public Optional<User> findById(int userId) {
            return Optional.ofNullable(users.get(userId));
        }

        public List<User> findAll() {
            return new ArrayList<>(users.values());
        }

        public boolean delete(int userId) {
            return users.remove(userId) != null;
        }
    }

    /** ユーザー管理のビジネスロジックを担当するサービス */
    public static class UserService {
        private final UserRepository repository;

        public UserService(UserRepository repository) {
            this.repository = repository;
        }

        public User createUser(String name, String email, int age) {
            if (!validateEmail(email)) {
                throw new IllegalArgumentException("Invalid email format: " + email);
            }
            if (!validateAge(age)) {
                throw new IllegalArgumentException("Invalid age: " + age);
            }
            User user = new User(0, name, email, age);
            return repository.save(user);
        }

        public User getUser(int userId) {
            return repository.findById(userId)
                .orElseThrow(() -> new IllegalStateException("User not found: " + userId));
        }

        public User updateUser(int userId, String name, String email, Integer age) {
            User user = getUser(userId);

            if (name != null) {
                user.setName(name);
            }
            if (email != null) {
                if (!validateEmail(email)) {
                    throw new IllegalArgumentException("Invalid email format: " + email);
                }
                user.setEmail(email);
            }
            if (age != null) {
                if (!validateAge(age)) {
                    throw new IllegalArgumentException("Invalid age: " + age);
                }
                user.setAge(age);
            }
            return repository.save(user);
        }

        public boolean deleteUser(int userId) {
            getUser(userId); // 存在確認
            return repository.delete(userId);
        }

        public List<User> listUsers() {
            return repository.findAll();
        }
    }
}
