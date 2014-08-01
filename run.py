#!/usr/bin/env python
from imods import app, db
from imods.db import add_admins_to_db

if __name__ == "__main__":
    if app.config["DEBUG"]:
        add_admins_to_db(app, db)
    app.run(debug=True, port=8000, host='0.0.0.0')
