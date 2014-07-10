PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE "USER" (
	uid INTEGER NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	password VARCHAR(200) NOT NULL, 
	fullname VARCHAR(200) NOT NULL, 
	age INTEGER, 
	author_identifier VARCHAR(100), 
	private_key VARCHAR NOT NULL, 
	PRIMARY KEY (uid), 
	UNIQUE (email)
);
INSERT INTO "USER" VALUES(1,'odayfans@gmail.com','asdasda','Ryan Feng',0,NULL,'asdjasd');
CREATE TABLE "CATEGORY" (
	cid INTEGER NOT NULL, 
	parent_id INTEGER, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(2000), 
	PRIMARY KEY (cid), 
	FOREIGN KEY(parent_id) REFERENCES "CATEGORY" (cid)
);
CREATE TABLE "DEVICE" (
	uid INTEGER, 
	device_name VARCHAR(200) NOT NULL, 
	"IMEI" VARCHAR(100) NOT NULL, 
	"UDID" VARCHAR(200) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	PRIMARY KEY ("UDID"), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid) ON DELETE CASCADE
);
CREATE TABLE "BILLING_INFO" (
	bid INTEGER NOT NULL, 
	uid INTEGER, 
	address VARCHAR(200) NOT NULL, 
	type_ VARCHAR(200) NOT NULL, 
	credit_card_no VARCHAR(100), 
	credit_card_expr_date DATE, 
	credit_card_name VARCHAR(200), 
	PRIMARY KEY (bid), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid)
);
CREATE TABLE "ITEM" (
	category_id INTEGER, 
	author_id VARCHAR(100), 
	package_name VARCHAR(200) NOT NULL, 
	display_name VARCHAR(100) NOT NULL, 
	package_version VARCHAR(100) NOT NULL, 
	package_signature VARCHAR, 
	package_path VARCHAR, 
	package_assets_path VARCHAR, 
	package_dependencies VARCHAR, 
	price FLOAT, 
	summary VARCHAR(500), 
	description VARCHAR, 
	add_date DATE NOT NULL, 
	last_update_date DATE NOT NULL, 
	CONSTRAINT "package_id_PK" PRIMARY KEY (package_name, package_version), 
	FOREIGN KEY(category_id) REFERENCES "CATEGORY" (cid) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES "USER" (author_identifier)
);
CREATE TABLE "ORDER" (
	oid INTEGER NOT NULL, 
	uid INTEGER, 
	pkg_name VARCHAR(200), 
	payment INTEGER, 
	quantity INTEGER NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	total_price FLOAT, 
	charged FLOAT, 
	order_date DATETIME NOT NULL, 
	PRIMARY KEY (oid), 
	FOREIGN KEY(uid) REFERENCES "USER" (uid) ON DELETE CASCADE, 
	FOREIGN KEY(pkg_name) REFERENCES "ITEM" (package_name), 
	FOREIGN KEY(payment) REFERENCES "BILLING_INFO" (bid)
);
COMMIT;
