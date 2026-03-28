# save as check_pharmacist.py
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    pharmacist = User.query.filter_by(role='pharmacist').first()
    if pharmacist:
        print(f"✅ Pharmacist found:")
        print(f"   Email: {pharmacist.email}")
        print(f"   Role: {pharmacist.role}")
        print(f"   Active: {pharmacist.is_active}")
    else:
        print("❌ No pharmacist user found!")
        print("Creating one now...")
        
        pharmacist = User()
        pharmacist.username = 'pharmacist'
        pharmacist.email = 'emailid.com'
        pharmacist.full_name = 'Default Pharmacist'
        pharmacist.role = 'pharmacist'
        pharmacist.is_active = True
        pharmacist.set_password('########')
        db.session.add(pharmacist)
        db.session.commit()
        print(f"✅ Pharmacist created: emailid.com / #######")
