import os
import sqlite3
from datetime import datetime, timezone

import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATABASE_DIR = os.path.join(
    PROJECT_ROOT,
    "database"
)

DATABASE_PATH = os.path.join(
    DATABASE_DIR,
    "face_auth.db"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def get_connection():
    """
    Create a connection to the SQLite database.
    """

    os.makedirs(
        DATABASE_DIR,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def initialize_database():
    """
    Create the database tables if they do not already exist.
    """

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id TEXT NOT NULL,

            external_user_id TEXT NOT NULL,

            active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT NOT NULL,

            UNIQUE(customer_id, external_user_id)
        )
        """
    )

    # --------------------------------------------------------
    # FACE TEMPLATES
    # --------------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS face_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            embedding BLOB NOT NULL,

            embedding_dimension INTEGER NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    connection.commit()

    connection.close()


# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(
    customer_id: str,
    external_user_id: str
):
    """
    Create a biometric user.

    The system does NOT require the person's name.

    Returns:
        integer database user ID
    """

    if not customer_id:
        raise ValueError(
            "customer_id cannot be empty."
        )

    if not external_user_id:
        raise ValueError(
            "external_user_id cannot be empty."
        )

    connection = get_connection()

    cursor = connection.cursor()

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    try:

        cursor.execute(
            """
            INSERT INTO users (
                customer_id,
                external_user_id,
                active,
                created_at
            )
            VALUES (?, ?, 1, ?)
            """,
            (
                customer_id,
                external_user_id,
                created_at
            )
        )

        connection.commit()

        user_id = cursor.lastrowid

    except sqlite3.IntegrityError:

        connection.close()

        raise ValueError(
            "This customer_id + external_user_id "
            "already exists."
        )

    connection.close()

    return user_id


def get_user(
    customer_id: str,
    external_user_id: str
):
    """
    Retrieve a user using the customer's identifiers.

    Returns:
        dict or None
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            customer_id,
            external_user_id,
            active,
            created_at
        FROM users
        WHERE customer_id = ?
          AND external_user_id = ?
        """,
        (
            customer_id,
            external_user_id
        )
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "customer_id": row[1],
        "external_user_id": row[2],
        "active": bool(row[3]),
        "created_at": row[4],
    }


def deactivate_user(
    customer_id: str,
    external_user_id: str
):
    """
    Disable a user's biometric authentication.
    """

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
            external_user_id
        )
    )

    connection.commit()

    changed_rows = cursor.rowcount

    connection.close()

    return changed_rows > 0


# ============================================================
# FACE TEMPLATE STORAGE
# ============================================================

def add_face_template(
    user_id: int,
    embedding
):
    """
    Store one InsightFace embedding.

    InsightFace embeddings are expected to be
    512-dimensional float32 vectors.
    """

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    )

    if embedding.ndim != 1:

        raise ValueError(
            "Embedding must be a 1D vector."
        )

    if embedding.shape[0] != 512:

        raise ValueError(
            f"Expected 512-dimensional embedding, "
            f"got {embedding.shape[0]}."
        )

    connection = get_connection()

    cursor = connection.cursor()

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute(
        """
        INSERT INTO face_templates (
            user_id,
            embedding,
            embedding_dimension,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            embedding.tobytes(),
            512,
            created_at
        )
    )

    connection.commit()

    template_id = cursor.lastrowid

    connection.close()

    return template_id


# ============================================================
# ATOMIC ENROLLMENT STORAGE
# ============================================================

def create_user_with_templates(
    customer_id: str,
    external_user_id: str,
    embeddings
):
    """
    Atomically create a user and store all biometric templates.

    Either the user and ALL templates are committed,
    or nothing is stored.

    This should be used by the production enrollment flow
    after biometric capture and quality checks have passed.
    """

    # --------------------------------------------------------
    # Validate identifiers
    # --------------------------------------------------------

    if not customer_id:

        raise ValueError(
            "customer_id cannot be empty."
        )

    if not external_user_id:

        raise ValueError(
            "external_user_id cannot be empty."
        )

    # --------------------------------------------------------
    # Validate embeddings collection
    # --------------------------------------------------------

    if not embeddings:

        raise ValueError(
            "At least one embedding is required."
        )

    validated_embeddings = []

    # --------------------------------------------------------
    # Validate every embedding BEFORE touching database
    # --------------------------------------------------------

    for embedding in embeddings:

        embedding = np.asarray(
            embedding,
            dtype=np.float32
        )

        if embedding.ndim != 1:

            raise ValueError(
                "Each embedding must be a 1D vector."
            )

        if embedding.shape[0] != 512:

            raise ValueError(
                "Every embedding must be "
                "512-dimensional."
            )

        validated_embeddings.append(
            embedding
        )

    # --------------------------------------------------------
    # Open database connection
    # --------------------------------------------------------

    connection = get_connection()

    try:

        cursor = connection.cursor()

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        # ====================================================
        # CREATE USER
        # ====================================================

        cursor.execute(
            """
            INSERT INTO users (
                customer_id,
                external_user_id,
                active,
                created_at
            )
            VALUES (?, ?, 1, ?)
            """,
            (
                customer_id,
                external_user_id,
                created_at
            )
        )

        user_id = cursor.lastrowid

        # ====================================================
        # INSERT ALL FACE TEMPLATES
        # ====================================================

        for embedding in validated_embeddings:

            cursor.execute(
                """
                INSERT INTO face_templates (
                    user_id,
                    embedding,
                    embedding_dimension,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    sqlite3.Binary(
                        embedding.tobytes()
                    ),
                    512,
                    created_at
                )
            )

        # ====================================================
        # COMMIT
        # ====================================================

        connection.commit()

        return {
            "user_id": user_id,
            "template_count": len(
                validated_embeddings
            )
        }

    except sqlite3.IntegrityError as error:

        # ----------------------------------------------------
        # Rollback EVERYTHING
        # ----------------------------------------------------

        connection.rollback()

        raise ValueError(
            "This customer_id + external_user_id "
            "already exists."
        ) from error

    except Exception:

        # ----------------------------------------------------
        # Rollback EVERYTHING
        # ----------------------------------------------------

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# RETRIEVE FACE TEMPLATES
# ============================================================

def get_face_templates(
    customer_id: str,
    external_user_id: str
):
    """
    Retrieve all face templates belonging to
    a particular external user.

    Returns:
        list of numpy arrays
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            ft.embedding,
            ft.embedding_dimension
        FROM face_templates ft
        JOIN users u
            ON ft.user_id = u.id
        WHERE u.customer_id = ?
          AND u.external_user_id = ?
          AND u.active = 1
        ORDER BY ft.id
        """,
        (
            customer_id,
            external_user_id
        )
    )

    rows = cursor.fetchall()

    connection.close()

    templates = []

    for embedding_blob, dimension in rows:

        if dimension != 512:
            continue

        embedding = np.frombuffer(
            embedding_blob,
            dtype=np.float32
        ).copy()

        templates.append(
            embedding
        )

    return templates


# ============================================================
# DELETE BIOMETRIC TEMPLATES
# ============================================================

def delete_face_templates(
    customer_id: str,
    external_user_id: str
):
    """
    Delete all biometric templates associated
    with a specific external user.

    The user record itself remains.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM face_templates
        WHERE user_id = (
            SELECT id
            FROM users
            WHERE customer_id = ?
              AND external_user_id = ?
        )
        """,
        (
            customer_id,
            external_user_id
        )
    )

    connection.commit()

    deleted_rows = cursor.rowcount

    connection.close()

    return deleted_rows