import os
import sys
import sqlite3


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from storage.database import (
    get_connection,
    initialize_database,
)


# ============================================================
# DISPLAY USERS
# ============================================================

def list_users():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id,
            u.customer_id,
            u.external_user_id,
            u.active,
            u.created_at,
            COUNT(ft.id) AS template_count
        FROM users u
        LEFT JOIN face_templates ft
            ON u.id = ft.user_id
        GROUP BY
            u.id,
            u.customer_id,
            u.external_user_id,
            u.active,
            u.created_at
        ORDER BY u.id
        """
    )

    rows = cursor.fetchall()

    connection.close()

    print()
    print("=" * 90)
    print("ENROLLED USERS")
    print("=" * 90)

    if not rows:

        print("No users enrolled.")

        return

    print(
        f"{'DB ID':<8}"
        f"{'CUSTOMER':<22}"
        f"{'USER ID':<22}"
        f"{'STATUS':<12}"
        f"{'TEMPLATES':<10}"
    )

    print("-" * 90)

    for row in rows:

        user_id = row[0]
        customer_id = row[1]
        external_user_id = row[2]
        active = row[3]
        template_count = row[5]

        status = (
            "ACTIVE"
            if active
            else "INACTIVE"
        )

        print(
            f"{user_id:<8}"
            f"{customer_id:<22}"
            f"{external_user_id:<22}"
            f"{status:<12}"
            f"{template_count:<10}"
        )

    print("=" * 90)


# ============================================================
# VIEW USER
# ============================================================

def view_user():

    customer_id = input(
        "Customer ID: "
    ).strip()

    external_user_id = input(
        "External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id,
            u.customer_id,
            u.external_user_id,
            u.active,
            u.created_at,
            COUNT(ft.id)
        FROM users u
        LEFT JOIN face_templates ft
            ON u.id = ft.user_id
        WHERE u.customer_id = ?
          AND u.external_user_id = ?
        GROUP BY u.id
        """,
        (
            customer_id,
            external_user_id,
        )
    )

    row = cursor.fetchone()

    connection.close()

    print()

    if row is None:

        print("❌ User not found.")

        return

    print("=" * 60)
    print("USER DETAILS")
    print("=" * 60)

    print(
        f"Database ID      : {row[0]}"
    )

    print(
        f"Customer ID      : {row[1]}"
    )

    print(
        f"External User ID : {row[2]}"
    )

    print(
        f"Status           : "
        f"{'ACTIVE' if row[3] else 'INACTIVE'}"
    )

    print(
        f"Created At       : {row[4]}"
    )

    print(
        f"Face Templates   : {row[5]}"
    )

    print("=" * 60)


# ============================================================
# EDIT USER IDENTIFIERS
# ============================================================

def edit_user():

    old_customer_id = input(
        "Current Customer ID: "
    ).strip()

    old_external_user_id = input(
        "Current External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE customer_id = ?
          AND external_user_id = ?
        """,
        (
            old_customer_id,
            old_external_user_id,
        )
    )

    row = cursor.fetchone()

    if row is None:

        connection.close()

        print("❌ User not found.")

        return

    print()
    print("Enter the new identifiers.")

    new_customer_id = input(
        "New Customer ID: "
    ).strip()

    new_external_user_id = input(
        "New External User ID: "
    ).strip()

    if not new_customer_id or not new_external_user_id:

        connection.close()

        print("❌ IDs cannot be empty.")

        return

    try:

        cursor.execute(
            """
            UPDATE users
            SET
                customer_id = ?,
                external_user_id = ?
            WHERE id = ?
            """,
            (
                new_customer_id,
                new_external_user_id,
                row[0],
            )
        )

        connection.commit()

        print()
        print("✅ User identifiers updated.")

    except sqlite3.IntegrityError:

        print()
        print(
            "❌ That customer + user ID "
            "combination already exists."
        )

    finally:

        connection.close()


# ============================================================
# DELETE FACE TEMPLATES
# ============================================================

def delete_templates():

    customer_id = input(
        "Customer ID: "
    ).strip()

    external_user_id = input(
        "External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id,
            COUNT(ft.id)
        FROM users u
        LEFT JOIN face_templates ft
            ON u.id = ft.user_id
        WHERE u.customer_id = ?
          AND u.external_user_id = ?
        GROUP BY u.id
        """,
        (
            customer_id,
            external_user_id,
        )
    )

    row = cursor.fetchone()

    if row is None:

        connection.close()

        print("❌ User not found.")

        return

    template_count = row[1]

    print()
    print(
        f"This will delete {template_count} "
        "biometric templates."
    )

    confirmation = input(
        'Type "DELETE" to confirm: '
    ).strip()

    if confirmation != "DELETE":

        connection.close()

        print("Operation cancelled.")

        return

    cursor.execute(
        """
        DELETE FROM face_templates
        WHERE user_id = ?
        """,
        (row[0],)
    )

    connection.commit()

    connection.close()

    print()
    print(
        f"✅ Deleted {template_count} "
        "biometric templates."
    )


# ============================================================
# DEACTIVATE USER
# ============================================================

def deactivate_user():

    customer_id = input(
        "Customer ID: "
    ).strip()

    external_user_id = input(
        "External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET active = 0
        WHERE customer_id = ?
          AND external_user_id = ?
        """,
        (
            customer_id,
            external_user_id,
        )
    )

    changed = cursor.rowcount

    connection.commit()
    connection.close()

    if changed:

        print()
        print("✅ User deactivated.")

    else:

        print()
        print("❌ User not found.")


# ============================================================
# REACTIVATE USER
# ============================================================

def reactivate_user():

    customer_id = input(
        "Customer ID: "
    ).strip()

    external_user_id = input(
        "External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET active = 1
        WHERE customer_id = ?
          AND external_user_id = ?
        """,
        (
            customer_id,
            external_user_id,
        )
    )

    changed = cursor.rowcount

    connection.commit()
    connection.close()

    if changed:

        print()
        print("✅ User reactivated.")

    else:

        print()
        print("❌ User not found.")


# ============================================================
# DELETE USER
# ============================================================

def delete_user():

    customer_id = input(
        "Customer ID: "
    ).strip()

    external_user_id = input(
        "External User ID: "
    ).strip()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            u.id,
            COUNT(ft.id)
        FROM users u
        LEFT JOIN face_templates ft
            ON u.id = ft.user_id
        WHERE u.customer_id = ?
          AND u.external_user_id = ?
        GROUP BY u.id
        """,
        (
            customer_id,
            external_user_id,
        )
    )

    row = cursor.fetchone()

    if row is None:

        connection.close()

        print("❌ User not found.")

        return

    print()
    print(
        f"User has {row[1]} biometric templates."
    )

    print(
        "This will permanently remove the "
        "user and their biometric templates."
    )

    confirmation = input(
        'Type "DELETE USER" to confirm: '
    ).strip()

    if confirmation != "DELETE USER":

        connection.close()

        print("Operation cancelled.")

        return

    cursor.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (row[0],)
    )

    connection.commit()

    connection.close()

    print()
    print("✅ User and biometric templates deleted.")


# ============================================================
# MENU
# ============================================================

def show_menu():

    while True:

        print()
        print("=" * 60)
        print("       FACE AUTHENTICATION DATABASE MANAGER")
        print("=" * 60)

        print("1. List enrolled users")
        print("2. View user")
        print("3. Edit user identifiers")
        print("4. Delete biometric templates")
        print("5. Deactivate user")
        print("6. Reactivate user")
        print("7. Delete user completely")
        print("8. Exit")

        print("=" * 60)

        choice = input(
            "Choose an option: "
        ).strip()

        if choice == "1":

            list_users()

        elif choice == "2":

            view_user()

        elif choice == "3":

            edit_user()

        elif choice == "4":

            delete_templates()

        elif choice == "5":

            deactivate_user()

        elif choice == "6":

            reactivate_user()

        elif choice == "7":

            delete_user()

        elif choice == "8":

            print()
            print("Database manager closed.")

            break

        else:

            print()
            print("❌ Invalid option.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    initialize_database()

    show_menu()