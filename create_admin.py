#!/usr/bin/env python3
"""
Admin Creation Script - Create admin users securely via command line
Run: python create_admin.py

This is the ONLY way to create admin accounts (for security)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
import getpass


def create_admin():
    """Create an admin user via command line"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 55)
        print("   🏥 SMART HOSPITAL - ADMIN ACCOUNT CREATION")
        print("=" * 55 + "\n")
        
        # Get admin details
        print("Enter admin account details:\n")
        
        username = input("  Username: ").strip()
        if not username or len(username) < 3:
            print("\n❌ Error: Username must be at least 3 characters!")
            return
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            print(f"\n❌ Error: Username '{username}' already exists!")
            return
        
        email = input("  Email: ").strip().lower()
        if not email or '@' not in email:
            print("\n❌ Error: Please enter a valid email address!")
            return
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            print(f"\n❌ Error: Email '{email}' is already registered!")
            return
        
        full_name = input("  Full Name: ").strip()
        if not full_name:
            print("\n❌ Error: Full name is required!")
            return
        
        password = getpass.getpass("  Password (min 6 chars): ")
        if len(password) < 6:
            print("\n❌ Error: Password must be at least 6 characters!")
            return
        
        confirm_password = getpass.getpass("  Confirm Password: ")
        if password != confirm_password:
            print("\n❌ Error: Passwords do not match!")
            return
        
        # Create admin user
        try:
            admin = User(
                username=username,
                email=email,
                full_name=full_name,
                role='admin',
                is_active=True
            )
            admin.set_password(password)
            
            db.session.add(admin)
            db.session.commit()
            
            print("\n" + "=" * 55)
            print("   ✅ ADMIN ACCOUNT CREATED SUCCESSFULLY!")
            print("=" * 55)
            print(f"\n   Username:  {username}")
            print(f"   Email:     {email}")
            print(f"   Full Name: {full_name}")
            print(f"   Role:      admin")
            print("\n   You can now login at /login")
            print("=" * 55 + "\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error creating admin: {str(e)}")
            return


def list_admins():
    """List all admin users"""
    app = create_app()
    
    with app.app_context():
        admins = User.query.filter_by(role='admin').all()
        
        print("\n" + "=" * 55)
        print("   📋 EXISTING ADMIN ACCOUNTS")
        print("=" * 55 + "\n")
        
        if not admins:
            print("   No admin accounts found.\n")
        else:
            for admin in admins:
                status = "✅ Active" if admin.is_active else "❌ Inactive"
                print(f"   • {admin.username} ({admin.email}) - {status}")
            print(f"\n   Total: {len(admins)} admin(s)\n")
        
        print("=" * 55 + "\n")


def main():
    """Main menu"""
    print("\n" + "=" * 55)
    print("   🏥 SMART HOSPITAL - ADMIN MANAGEMENT")
    print("=" * 55)
    print("\n   1. Create new admin account")
    print("   2. List existing admin accounts")
    print("   3. Exit")
    
    choice = input("\n   Enter choice (1-3): ").strip()
    
    if choice == '1':
        create_admin()
    elif choice == '2':
        list_admins()
    elif choice == '3':
        print("\n   Goodbye! 👋\n")
    else:
        print("\n   Invalid choice. Please try again.")
        main()


if __name__ == '__main__':
    main()