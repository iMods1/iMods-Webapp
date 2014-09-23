""" Constants and enumerations used by other modules.
"""


class BillingType:
    creditcard = 'creditcard'
    paypal = 'paypal'


class UserRole:
    SiteAdmin = 0
    Admin = 1
    AppDev = 50
    User = 100


class AccountStatus:
    Registered = 0
    Activated = 1
    Suspended = 1000


class OrderStatus:
    OrderPlaced = 0
    OrderCompleted = 1
    OrderCancelled = 2
