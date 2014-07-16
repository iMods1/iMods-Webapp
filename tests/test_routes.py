#!/usr/bin/env python
import os
from flask import json
from copy import copy
import unittest
from tempfile import mkstemp
import sys
sys.path.append('')
import imods
from imods.models import UserRole, OrderStatus


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.dbpath = mkstemp()
        imods.app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + self.dbpath
        imods.app.config["DEBUG"] = True
        imods.app.config["TESTING"] = True
        self.app = imods.app
        imods.init_db()
        self.db = imods.db

    def tearDown(self):
        os.close(self.db_fd)
        # unlink actually removes the file
        os.unlink(self.dbpath)

    def post_json(self, server, url, data):
        return server.post(url, data=json.dumps(data),
                           content_type="application/json")

    def user_register(self, server, name, email, pwd, age):
        data = json.dumps(dict(
            fullname=name,
            email=email,
            password=pwd,
            age=int(age)
        ))
        return self.post_json(server, "/api/user/register", data)

    def user_login(self, server, email, pwd):
        data = json.dumps(dict(
            email=email,
            password=pwd
        ))
        return self.post_json(server, "/api/user/login", data)

    def user_logout(self, server):
        return server.get("/api/user/logout")

    def test_user_register(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "ryan", "ryan@ryan.com",
                                    "ryan123", 10)
            assert rv.status_code == 200
            js = json.loads(rv.data)
            assert js["fullname"] == "ryan"
            assert js["email"] == "ryan@ryan.com"
            assert js["age"] == 10

    def test_login_logout(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "ryan", "ryan@ryan.com",
                                    "ryan123", 10)
            assert rv.status_code == 200
            rv = self.user_login(server, "ryan@ryan.com", "ryan123")
            assert rv.status_code == 200
            rv = self.user_logout(server)
            assert rv.status_code == 200
            assert 'successful' in rv.data

    def test_login_fail(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "ryan", "ryan@ryan.com",
                                    "ryan123", 10)
            assert rv.status_code == 200
            rv = self.user_login(server, "ryan@ryan.com", "ryan321")
            assert rv.status_code != 200
            assert 'Invalid email and password' in rv.data

    def test_register_fail(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "ryan1", "ryan1@ryan.com",
                                    "ryan123", 10)
            assert rv.status_code == 200
            rv = self.user_register(server, "ryan1", "ryan1@ryan.com",
                                    "ryan123", 10)
            assert rv.status_code == 409
            assert 'already registered' in rv.data

    def test_user_update(self):
        with self.app.test_client() as server:
            self.user_register(server, "world", "world@hello.com",
                               "world123", 10)
            self.user_login(server, "world@hello.com", "world123")
            data = dict(fullname="hello", old_password="world123",
                        new_password="hello123", age=20)
            rv = self.post_json(server, "/api/user/update", data)
            assert rv.status_code == 200
            assert 'successful' in rv.data

    def test_user_profile(self):
        with self.app.test_client() as server:
            self.user_register(server, "profile1", "profile1@profile.com",
                               "profile123", 99)
            rv = self.user_login(server, "profile1@profile.com", "profile123")
            assert rv.status_code == 200

            rv = server.get("/api/user/profile")
            assert rv.status_code == 200
            js = json.loads(rv.data)
            assert js['fullname'] == "profile1"
            assert js['email'] == 'profile1@profile.com'
            assert js['age'] == 99

    def test_device(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "device1", "device1@device.com",
                                    "device123", 99)
            assert rv.status_code == 200
            rv = self.user_login(server, "device1@device.com", "device123")
            assert rv.status_code == 200
            rv = server.get("/api/user/profile")
            assert rv.status_code == 200
            uid = json.loads(rv.data)['uid']

            data = dict(
                device_name="device1",
                imei="12371237913727927312",
                udid="da9s8dj9adj98j98j12dkljasd",
                model="iPad123,31"
            )
            rv = self.post_json(server, "/api/device/add", data)
            assert rv.status_code == 200

            rv = server.get("/api/device/list")
            assert rv.status_code == 200
            assert len(json.loads(rv.data)) > 0

            js1 = json.loads(rv.data)
            assert js1[0]['device_name'] == data['device_name']
            assert js1[0]['IMEI'] == data['imei']
            assert js1[0]['UDID'] == data['udid']
            assert js1[0]['model'] == data['model']
            assert js1[0]['uid'] == uid

            rv = server.get("/api/device/%d" % js1[0]['dev_id'])
            assert rv.status_code == 200
            assert len(json.loads(rv.data)) > 1

            js2 = json.loads(rv.data)
            assert js2['dev_id'] == js1[0]['dev_id']
            assert js2['device_name'] == data['device_name']
            assert js2['IMEI'] == data['imei']
            assert js2['UDID'] == data['udid']
            assert js2['model'] == data['model']
            assert js2['uid'] == uid

    def test_category(self):
        with self.app.test_client() as server:
            self.user_register(server, "category_admin",
                               "category@category.com", "category123", 99)
            self.user_login(server, "category@category.com", "category123")
            # Need admin roles to add a category
            with server.session_transaction() as se:
                se['user']['role'] = UserRole.SiteAdmin
            # Root category
            data1 = dict(
                name="category1",
                description="description1"
            )
            rv1 = self.post_json(server, "/api/category/add", data1)
            assert rv1.status_code == 200
            js1 = json.loads(rv1.data)
            assert js1["name"] == data1["name"]
            assert js1["description"] == data1["description"]

            # Add sub-category
            data2 = copy(data1)
            data2["parent_id"] = js1["cid"]
            data2["name"] = "subcategory1"
            data2["description"] = "subcategory description1"
            rv2 = self.post_json(server, "/api/category/add", data2)
            assert rv2.status_code == 200
            js2 = json.loads(rv2.data)
            assert js2["name"] == data2["name"]
            assert js2["description"] == data2["description"]

            data3 = copy(data1)
            data3["name"] = "category updated"
            data3["description"] = "description updated"
            rv3 = self.post_json(server,
                                 "/api/category/%d/update" % js1["cid"], data3)
            assert rv3.status_code == 200
            assert 'successful' in rv3.data

            rv3 = server.get("/api/category/%d" % js2["cid"])
            assert rv3.status_code == 200
            js3 = json.loads(rv3.data)
            assert js3['parent_id'] == js1["cid"]

            rv4 = server.get("/api/category/%d/delete" % js1["cid"])
            assert rv4.status_code == 409
            assert 'not empty' in rv4.data

            rv4 = server.get("/api/category/%d/delete" % js2["cid"])
            assert rv4.status_code == 200
            assert 'successful' in rv4.data

            rv5 = server.get("/api/category/%d" % js2["cid"])
            assert rv5.status_code == 500
            assert "not found" in rv5.data

    def test_billing(self):
        with self.app.test_client() as server:
            rv = self.user_register(server, "billing", "billing@billing.com",
                                    "billing123", 99)
            assert rv.status_code == 200
            user = json.loads(rv.data)
            rv = self.user_login(server, "billing@billing.com", "billing123")
            assert rv.status_code == 200

            data1 = dict(
                address="billing address1",
                zipcode=12345,
                state="state1",
                country="country1",
                type_="creditcard",
                cc_no="2312321312312312",
                cc_name="billing name1",
                cc_expr="12/15"
            )
            rv1 = self.post_json(server, "/api/billing/add", data1)
            assert rv1.status_code == 200
            js1 = json.loads(rv1.data)
            assert js1["uid"] == user["uid"]
            assert js1["address"] == data1["address"]
            assert js1["zipcode"] == data1["zipcode"]
            assert js1["state"] == data1["state"]
            assert js1["country"] == data1["country"]
            assert js1["type_"] == data1["type_"]

            rv2 = server.get("/api/billing/%d" % js1["bid"])
            assert rv2.status_code == 200
            js2 = json.loads(rv2.data)
            assert js2["uid"] == user["uid"]
            assert js2["address"] == data1["address"]
            assert js2["zipcode"] == data1["zipcode"]
            assert js2["state"] == data1["state"]
            assert js2["country"] == data1["country"]
            assert js2["type_"] == data1["type_"]

            data2 = copy(data1)
            data2["address"] = "address updated"
            data2["zipcode"] = 312312
            data2["state"] = "state updated"
            data2["country"] = "country updated"
            data2["type_"] = "paypal"
            data2["cc_no"] = "19591233123"
            data2["cc_name"] = "billing name updated"
            data2["cc_expr"] = "05/18"
            rv3 = self.post_json(server, "/api/billing/%d/update" % js2["bid"],
                                         data2)
            assert rv3.status_code == 200
            assert "successful" in rv3.data

            rv4 = server.get("/api/billing/%d" % js2["bid"])
            assert rv4.status_code == 200
            js4 = json.loads(rv4.data)
            assert js4["uid"] == js2["uid"]
            assert js4["address"] == data2["address"]
            assert js4["zipcode"] == data2["zipcode"]
            assert js4["state"] == data2["state"]
            assert js4["country"] == data2["country"]
            assert js4["type_"] == data2["type_"]

            rv5 = server.get("/api/billing/%d/delete" % js2["bid"])
            assert rv5.status_code == 200
            assert 'successful' in rv5.data

            rv6 = server.get("/api/billing/%d" % js2["bid"])
            assert rv6.status_code == 500
            assert 'not found' in rv6.data

    def test_item(self):
        with self.app.test_client() as server:
            user = self.user_register(server, "item1", "item1@item.com",
                                      "item123", 33)
            user = json.loads(user.data)
            self.user_login(server, "item1@item.com", "item123")

            data1 = dict(
                pkg_name="package1",
                pkg_version="version1",
                display_name="Fine Package1",
                price=0.99,
                summary="summary1",
                description="description1",
                pkg_dependencies="dep1, dep2>0.5"
            )
            rv1 = self.post_json(server, "/api/item/add", data1)
            assert rv1.status_code == 200
            js1 = json.loads(rv1.data)
            assert js1["author_id"] == user["author_identifier"]
            assert js1["pkg_name"] == data1["pkg_name"]
            assert js1["pkg_version"] == data1["pkg_version"]
            assert js1["display_name"] == data1["display_name"]
            assert js1["price"] == data1["price"]
            assert js1["summary"] == data1["summary"]
            assert js1["description"] == data1["description"]
            assert js1["pkg_dependencies"] == data1["pkg_dependencies"]

            data2 = copy(data1)
            data2["pkg_name"] = "package1 updated"
            data2["pkg_version"] = "version1 updated"
            data2["display_name"] = "Fine Package1 updated"
            data2["price"] = 1.99
            data2["summary"] = "summary1 updated"
            data2["description"] = "description1 updated"
            data2["pkg_dependencies"] = "dep3, dep5<2.0"
            rv2 = self.post_json(server, "/api/item/%d/update" % js1["iid"],
                                 data2)
            assert rv2.status_code == 200
            assert 'successful' in rv2.data

            rv2 = server.get("/api/item/%d" % js1["iid"])
            assert rv2.status_code == 200
            js2 = json.loads(rv2.data)
            assert js2["pkg_name"] == data2["pkg_name"]
            assert js2["pkg_version"] == data2["pkg_version"]
            assert js2["display_name"] == data2["display_name"]
            assert js2["price"] == data2["price"]
            assert js2["summary"] == data2["summary"]
            assert js2["description"] == data2["description"]
            assert js2["pkg_dependencies"] == data2["pkg_dependencies"]

            rv3 = server.get("/api/item/%d/delete" % js1["iid"])
            assert rv3.status_code == 200
            assert 'successful' in rv3.data

            rv4 = server.get("/api/item/%d" % js1["iid"])
            assert rv4.status_code == 500
            assert 'not found' in rv4.data

    def test_order(self):
        with self.app.test_client() as server:
            user = self.user_register(server, "order1", "order1@order.com",
                                      "order123", 77)
            assert user.status_code == 200
            user = json.loads(user.data)
            rv = self.user_login(server, "order1@order.com", "order123")
            assert rv.status_code == 200

            data1 = dict(
                pkg_name="package_item1",
                pkg_version="version1",
                display_name="Fine Package1",
                price=0.99,
                summary="summary1",
                description="description1",
                dependencies="dep1, dep2>0.5"
            )
            item = self.post_json(server, "/api/item/add", data1)
            assert item.status_code == 200
            item = json.loads(item.data)

            data2 = dict(
                address="billing address1",
                zipcode=12345,
                state="state1",
                country="country1",
                type_="creditcard",
                cc_no="2312321312312312",
                cc_name="billing name1",
                cc_expr="12/15"
            )
            billing = self.post_json(server, "/api/billing/add", data2)
            billing = json.loads(billing.data)

            data3 = dict(
                billing_id=billing['bid'],
                item_id=item['iid'],
                total_price=item['price'],
                total_charged=item['price']+1.99
            )
            rv1 = self.post_json(server, "/api/order/add", data3)
            assert rv1.status_code == 200
            js1 = json.loads(rv1.data)
            assert js1["uid"] == user["uid"]
            assert js1["billing_id"] == data3["billing_id"]
            assert js1["pkg_name"] == data1["pkg_name"]
            assert js1["total_price"] == data3["total_price"]
            assert js1["total_charged"] == data3["total_charged"]
            assert js1["quantity"] == 1
            assert js1["currency"] == "USD"

            rv2 = server.get("/api/order/%d" % js1["oid"])
            assert rv2.status_code == 200
            js2 = json.loads(rv2.data)
            assert js2["billing_id"] == data3["billing_id"]
            assert js2["pkg_name"] == data1["pkg_name"]
            assert js2["total_price"] == data3["total_price"]
            assert js2["total_charged"] == data3["total_charged"]
            assert js2["quantity"] == 1
            assert js2["currency"] == "USD"

            rv3 = server.get("/api/order/%d/cancel" % js1["oid"])
            assert rv3.status_code == 200
            assert 'successful' in rv3.data

            rv4 = server.get("/api/order/%d" % js1["oid"])
            js4 = json.loads(rv4.data)
            assert rv4.status_code == 200
            assert js4["status"] == OrderStatus.OrderCancelled


if __name__ == "__main__":
    unittest.main()
