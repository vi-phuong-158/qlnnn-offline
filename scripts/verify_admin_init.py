import os
import sys
import tempfile
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import database.connection
from database.models import init_database, verify_user, get_connection

def test_admin_initialization():
    print("🧪 Starting Admin Initialization Security Test...")

    # Create a temp directory for our test databases
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path_a = Path(temp_dir) / "test_db_a.db"
        db_path_b = Path(temp_dir) / "test_db_b.db"

        # === TEST CASE A: Environment Variable Set ===
        print("\n[Case A] Testing with QLNNN_ADMIN_PASSWORD set...")

        # Monkeypatch database.connection.DATABASE_PATH
        database.connection.DATABASE_PATH = db_path_a
        # Ensure connection is reset
        database.connection.close_connection()

        test_pass = "secure_test_password_123"
        os.environ["QLNNN_ADMIN_PASSWORD"] = test_pass

        try:
            init_database()
            user = verify_user("admin", test_pass)
            if user:
                print("✅ PASSED: Admin created with env var password.")
            else:
                print("❌ FAILED: Admin creation with env var failed.")
                sys.exit(1)
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # === TEST CASE B: No Environment Variable (Random Generation) ===
        print("\n[Case B] Testing with NO environment variable (Generation)...")

        # Switch to new DB
        database.connection.DATABASE_PATH = db_path_b
        database.connection.close_connection()

        if "QLNNN_ADMIN_PASSWORD" in os.environ:
            del os.environ["QLNNN_ADMIN_PASSWORD"]

        try:
            init_database()

            # Verify "admin123" does NOT work
            user_default = verify_user("admin", "admin123")
            if user_default:
                print("❌ FAILED: Security vulnerability! 'admin123' still works.")
                sys.exit(1)
            else:
                print("✅ PASSED: 'admin123' rejected.")

            # Verify user exists (we can't know the password, but we can check the user exists)
            conn = get_connection()
            res = conn.execute("SELECT username FROM users WHERE username='admin'").fetchone()
            if res:
                print("✅ PASSED: Admin user exists (with unknown random password).")
            else:
                print("❌ FAILED: Admin user was not created.")
                sys.exit(1)

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("\n🎉 All security tests passed!")

if __name__ == "__main__":
    test_admin_initialization()
