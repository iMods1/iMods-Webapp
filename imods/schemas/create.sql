CREATE TABLE IF NOT EXISTS "USER"(
    "uid" INT NOT NULL ,
    "email" VARCHAR(200) NOT NULL UNIQUE,
    "password" VARCHAR(200) NOT NULL,
    "first_name" VARCHAR(50) NOT NULL,
    "last_name" VARCHAR(50) NOT NULL,
    "age" INT NOT NULL,
    "address" VARCHAR(200) NOT NULL,
    "author_identifier" CHAR(200) NOT NULL, -- author identifier for app, and any other contents
    "private_key" VARCHAR NOT NULL UNIQUE, -- keys for various encryption use
    PRIMARY KEY ("uid", "email")
);

-- Contains all registered devices with their owner id
CREATE TABLE IF NOT EXISTS "DEVICE"(
    "uid" INT REFERENCES "USER"("uid"),
    -- the user defined device name, retrieved when registering
    -- If it's empty, automatically create one based on model and user's real name
    "device_name" VARCHAR(200) NOT NULL,
    "IMEI" CHAR(100) NOT NULL UNIQUE,
    "UDID" CHAR(200) NOT NULL UNIQUE,
    "model" CHAR(100) NOT NULL,
    PRIMARY KEY("IMEI", "UDID")
);

CREATE TABLE IF NOT EXISTS "BILLING_INFO"(
    "bid" INT NOT NULL,
    "uid" INT REFERENCES "USER"("uid"),

    -- billing address, should match credit card's billing address,
    -- otherwise payment may fail
    "address" VARCHAR(200) NOT NULL,
    "type" VARCHAR(200) NOT NULL, -- billing type, either 'empty', 'creditcard' or 'paypal'

    -- credit card info may be empty because "type" maybe 'paypal'
    -- user also don't need to provide credit info for free content
    -- DO NOT STORE CVV NUMBER!
    "credit_card_no" CHAR(100),
    "credit_card_expr_date" DATE,
    "credit_card_name" CHAR(200),
    PRIMARY KEY("bid")
);

CREATE TABLE IF NOT EXISTS "CATEGORY"(
    "cid" INT NOT NULL ,
    "name" VARCHAR(100),
    "parent_id" INT REFERENCES "CATEGORY"("cid"),
    "description" VARCHAR,
    PRIMARY KEY("cid")
);

CREATE TABLE IF NOT EXISTS "ITEM"(
    "iid" INT NOT NULL ,
    "author_id" CHAR(200) REFERENCES "USER"("author_identifier"),
    "uniq_name" CHAR(200) NOT NULL, -- unique package name string to identify an item, e.g. coreutils, binutils etc
    "display_name" VARCHAR NOT NULL, -- display name in the store
    "version" CHAR(100) NOT NULL,
    "package_signature" VARCHAR NOT NULL, -- the signature of the package file stored on the repo server (AWS S3)
    "package_path" VARCHAR NOT NULL, -- path of the package file stored on the repo server (AWS S3)
    "preview_assets_path" VARCHAR NOT NULL, -- path of the preview assets
    "price" FLOAT,
    "summary" CHAR(500),
    "description" VARCHAR,
    "icon_path" VARCHAR, -- path to the icon file (Use S3)
    "category_id" INT REFERENCES "CATEGORY"("cid"),
    "add_date" DATE NOT NULL,
    "last_update_date" DATE NOT NULL,
    PRIMARY KEY("iid")
);

CREATE TABLE IF NOT EXISTS "DEPENDENCY"(
    "dep_id" INT NOT NULL ,
    "package_id" INT REFERENCES "ITEM"("iid"),
    "dependency_id" INT REFERENCES "ITEM"("iid"),
    PRIMARY KEY("dep_id")
);

CREATE TABLE IF NOT EXISTS "ORDER"(
    "oid" INT NOT NULL,
    "uid" INT REFERENCES "USER"("uid"),
    "item_it" INT REFERENCES "ITEM"("iid"),
    -- no quantity, it should always be one, maybe add gift feature later
    "total_price" FLOAT NOT NULL, -- might be different from the item price(e.g. using a promotion code or deal)
    "currency" CHAR(3) NOT NULL, -- currency code
    "order_date" DATE NOT NULL,
    PRIMARY KEY ("oid")
);

CREATE UNIQUE INDEX IF NOT EXISTS "DEP_IDX" ON "DEPENDENCY"("package_id");
