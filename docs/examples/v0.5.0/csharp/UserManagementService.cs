// 合成サンプル：ユーザー管理サービス（実在のシステムとは無関係）
using System;
using System.Collections.Generic;

namespace Example.Users
{
    /// <summary>ユーザー1件。</summary>
    public class User
    {
        public string UserId { get; }
        public string UserName { get; set; }
        public string Email { get; set; }
        public int Age { get; set; }

        public User(string userId, string userName, string email, int age)
        {
            UserId = userId;
            UserName = userName;
            Email = email;
            Age = age;
        }
    }

    public class UserNotFoundException : Exception
    {
        public UserNotFoundException(string userId) : base("user not found: " + userId) { }
    }

    public class UserAlreadyExistsException : Exception
    {
        public UserAlreadyExistsException(string userId) : base("user already exists: " + userId) { }
    }

    #region Service
    /// <summary>登録・更新・検索を行うサービス。</summary>
    public class UserManagementService
    {
        private readonly Dictionary<string, User> _users = new Dictionary<string, User>();
        private const int MinAge = 0;
        private const int MaxAge = 150;

        public int UserCount => _users.Count;

        public User RegisterUser(string userId, string userName, string email, int age)
        {
            ValidateUserId(userId);
            ValidateUserName(userName);
            ValidateEmail(email);
            ValidateAge(age);
            if (_users.ContainsKey(userId))
            {
                throw new UserAlreadyExistsException(userId);
            }
            var user = new User(userId, userName, email, age);
            _users[userId] = user;
            return user;
        }

        public User FindById(string userId)
        {
            return FindUserOrThrow(userId);
        }

        public List<User> FindAll()
        {
            var result = new List<User>();
            foreach (var user in _users.Values)
            {
                result.Add(user);
            }
            return result;
        }

        public List<User> FindByAgeRange(int minAge, int maxAge)
        {
            if (minAge > maxAge)
            {
                throw new ArgumentException("minAge must not exceed maxAge");
            }
            var result = new List<User>();
            foreach (var user in _users.Values)
            {
                if (user.Age >= minAge && user.Age <= maxAge)
                {
                    result.Add(user);
                }
            }
            return result;
        }

        public List<User> FindByEmailDomain(string domain)
        {
            var result = new List<User>();
            foreach (var user in _users.Values)
            {
                if (user.Email.EndsWith("@" + domain))
                {
                    result.Add(user);
                }
            }
            return result;
        }

        public User UpdateUser(string userId, string userName, string email, int age)
        {
            var user = FindUserOrThrow(userId);
            ValidateUserName(userName);
            ValidateEmail(email);
            ValidateAge(age);
            user.UserName = userName;
            user.Email = email;
            user.Age = age;
            return user;
        }

        public bool DeleteUser(string userId)
        {
            try
            {
                FindUserOrThrow(userId);
            }
            catch (UserNotFoundException)
            {
                return false;
            }
            finally
            {
                Log("delete attempted: " + userId);
            }
            return _users.Remove(userId);
        }

        private User FindUserOrThrow(string userId)
        {
            if (!_users.TryGetValue(userId, out var user))
            {
                throw new UserNotFoundException(userId);
            }
            return user;
        }

        private static void ValidateUserId(string userId)
        {
            if (string.IsNullOrWhiteSpace(userId))
            {
                throw new ArgumentException("userId is required");
            }
        }

        private static void ValidateUserName(string userName)
        {
            if (string.IsNullOrWhiteSpace(userName) || userName.Length > 50)
            {
                throw new ArgumentException("userName must be 1..50 characters");
            }
        }

        private static void ValidateEmail(string email)
        {
            if (string.IsNullOrWhiteSpace(email) || !email.Contains("@"))
            {
                throw new ArgumentException("email must contain @");
            }
        }

        private static void ValidateAge(int age)
        {
            switch (age)
            {
                case < MinAge:
                    throw new ArgumentException("age must not be negative");
                case > MaxAge:
                    throw new ArgumentException("age is out of range");
                default:
                    break;
            }
        }

        private static void Log(string message)
        {
            Console.WriteLine(DateTime.Now.ToString("s") + " " + message);
        }
    }
    #endregion
}
