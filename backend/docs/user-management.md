---
icon: lucide/user-plus
---

# User Management

This document outlines the user roles, permissions, and the processes for creating and managing users within the FastAPI Backend Template.

## User Roles

The system employs Role-Based Access Control (RBAC) with three distinct roles:

| Role | Description |
| :--- | :--- |
| **Super User (`super`)** | The highest level of access. Can manage all users, including other Super Users and Admins. |
| **Admin (`admin`)** | Staff-level administrator. Can manage regular users but cannot see or modify Super Users or other Admins. |
| **User (`user`)** | Standard end-user. Has access to their own data (e.g., ToDo lists) but no administrative privileges. |

---

## Permissions Matrix

| Action | Super User | Admin | User |
| :--- | :---: | :---: | :---: |
| Create Super User | ✅ | ❌ | ❌ |
| Create Admin | ✅ | ❌ | ❌ |
| Create Regular User | ✅ | ✅ | ❌ |
| View All Users | ✅ | ✅ (Excl. Super) | ❌ |
| Update Any User Role | ✅ | ❌ | ❌ |
| Update Regular User | ✅ | ✅ | ❌ |
| Delete Any User | ✅ | ✅ (Excl. Super/Admin) | ❌ |
| Self-Update Profile | ✅ | ✅ | ✅ |

---

## User Creation

### 1. Administrative Creation (Internal)
Super Users and Admins can create new users via the `POST /api/v1/users/` endpoint.

**Restrictions:**
- **Admins** can only create users with the `user` role. Attempting to create a `super` or `admin` will result in a `403 Forbidden` error.
- **Super Users** can create users with any role.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true
}
```

### 2. Public Registration
New users can register themselves via the `POST /api/v1/login/register` endpoint. All self-registered users are assigned the `user` role by default.

---

## Upgrading User Roles

Roles can be updated using the `PATCH /api/v1/users/{id}` endpoint.

### Upgrading Admin to Super User
Only an existing **Super User** can upgrade an **Admin** to a **Super User**.

**Example Request:**
- **URL:** `/api/v1/users/{admin_user_id}`
- **Method:** `PATCH`
- **Body:**
  ```json
  {
    "role": "super"
  }
  ```

**Security Notes:**
- Users cannot change their own `role` or `is_active` status.
- Admins cannot upgrade a regular `user` to `admin` or `super`.
