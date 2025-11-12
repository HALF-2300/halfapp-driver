"""
Simple script to create an initial admin invite code.
Run this to bootstrap the admin system.
"""
import sys
import os
sys.path.append('/app')

from database import get_db, engine, Base
from models.admin_invite import AdminInvite
import secrets
import string

def generate_access_code(length: int = 12) -> str:
    """Generate a secure random access code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_bootstrap_invite():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = next(get_db())
    
    try:
        # Check if we already have invites
        existing = db.query(AdminInvite).first()
        if existing:
            print("Admin invites already exist. First unused invite:")
            unused = db.query(AdminInvite).filter(AdminInvite.is_used == False).first()
            if unused:
                print(f"Access Code: {unused.access_code}")
            else:
                print("All invites have been used.")
            return
        
        # Create first admin invite
        access_code = generate_access_code()
        invite = AdminInvite(
            access_code=access_code,
            created_by="system",
            description="Bootstrap admin invite"
        )
        
        db.add(invite)
        db.commit()
        
        print(f"✅ Bootstrap admin invite created!")
        print(f"Access Code: {access_code}")
        print(f"Use this code at: http://localhost:3000/admin-access")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_bootstrap_invite()