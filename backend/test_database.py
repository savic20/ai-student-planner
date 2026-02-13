#!/usr/bin/env python3
"""
Database Test Script
--------------------
Run this to verify your database setup is working.

USAGE:
    cd backend
    source venv/bin/activate
    python test_database.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.db import (
    engine, Base, SessionLocal, check_db_connection,
    User, Syllabus, Chat, Message, Plan, Feedback, TokenUsage
)
from app.config import settings


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_connection():
    """Test database connection"""
    print_section("TEST 1: Database Connection")
    
    if check_db_connection():
        print("✅ Successfully connected to database")
        print(f"   URL: {settings.DATABASE_URL.split('@')[-1]}")  # Hide password
        return True
    else:
        print("❌ Failed to connect to database")
        print("   Make sure PostgreSQL is running: docker-compose up -d postgres")
        return False


def test_tables():
    """Test table creation"""
    print_section("TEST 2: Table Creation")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Get list of tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


def test_insert():
    """Test inserting data"""
    print_section("TEST 3: Insert Test Data")
    
    db = SessionLocal()
    try:
        # Create a test user
        test_user = User(
            email="test@example.com",
            hashed_password="dummy_hash",
            full_name="Test User",
            semester="Fall 2024",
            major="Computer Science"
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"✅ Created test user:")
        print(f"   ID: {test_user.id}")
        print(f"   Email: {test_user.email}")
        print(f"   Name: {test_user.full_name}")
        
        return test_user.id
    except Exception as e:
        print(f"❌ Failed to insert data: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def tst_query(user_id: int):
    """Test querying data"""
    print_section("TEST 4: Query Test Data")
    
    db = SessionLocal()
    try:
        # Query the user
        user = db.query(User).filter_by(id=user_id).first()
        
        if user:
            print(f"✅ Successfully queried user:")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Created: {user.created_at}")
            return True
        else:
            print(f"❌ User not found")
            return False
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False
    finally:
        db.close()


def test_relationships():
    """Test model relationships"""
    print_section("TEST 5: Relationship Test")
    
    db = SessionLocal()
    try:
        # Get a user
        user = db.query(User).first()
        
        # Create a chat
        chat = Chat(
            user_id=user.id,
            title="Test Chat"
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        
        # Create a message
        message = Message(
            chat_id=chat.id,
            role="user",
            content="Hello, this is a test message!"
        )
        db.add(message)
        db.commit()
        
        # Test relationship access
        print(f"✅ Created chat with ID: {chat.id}")
        print(f"✅ User has {len(user.chats)} chat(s)")
        print(f"✅ Chat has {len(chat.messages)} message(s)")
        
        return True
    except Exception as e:
        print(f"❌ Relationship test failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def cleanup():
    """Clean up test data"""
    print_section("CLEANUP: Removing Test Data")
    
    db = SessionLocal()
    try:
        # Delete test user (cascades to chats and messages)
        test_user = db.query(User).filter_by(email="test@example.com").first()
        if test_user:
            db.delete(test_user)
            db.commit()
            print("✅ Test data cleaned up")
        return True
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  STUDENT PLANNER - DATABASE TEST SUITE")
    print("=" * 70)
    
    # Test 1: Connection
    if not test_connection():
        print("\n❌ DATABASE CONNECTION FAILED - Fix this first!")
        return False
    
    # Test 2: Tables
    if not test_tables():
        print("\n❌ TABLE CREATION FAILED")
        return False
    
    # Test 3: Insert
    user_id = test_insert()
    if not user_id:
        print("\n❌ INSERT TEST FAILED")
        return False
    
    # Test 4: Query
    if not tst_query(user_id):
        print("\n❌ QUERY TEST FAILED")
        return False
    
    # Test 5: Relationships
    if not test_relationships():
        print("\n❌ RELATIONSHIP TEST FAILED")
        return False
    
    # Cleanup
    cleanup()
    
    # Summary
    print_section("✅ ALL TESTS PASSED!")
    print("\nYour database is set up correctly!")
    print("\nNext steps:")
    print("  1. Initialize Alembic migrations")
    print("  2. Create your first migration")
    print("  3. Start building the authentication system")
    print("\n" + "=" * 70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
