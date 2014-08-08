from models import User, UserRole
from werkzeug import generate_password_hash


def add_admins_to_db(app, db):
    # Add admin users to database
    for adm in app.config["ADMINS"]:
        if User.query.filter_by(email=adm['email']).first():
            return
        usr = User(fullname='admin',
                   email=adm['email'],
                   password=generate_password_hash(adm['password']),
                   author_identifier=adm["author_id"],
                   private_key="asdasdad",
                   role=UserRole.SiteAdmin)
        db.session.add(usr)
        db.session.commit()
