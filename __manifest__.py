{
    'name': 'Hotel Management',
    'version': '1.1',
    'summary': 'Comprehensive Hotel Management System',
    'description': """
        Hotel Management System
        ======================
        - Room and Guest Management
        - Booking System
        - Invoice and Payment Tracking
        - Additional Services
        - Custom Reports
    """,
    'author': 'Hani salim',
    'website': '',
    'depends': ['base', 'mail', 'sale', 'product', 'account', 'stock', 'purchase', 'web', 'website'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/product_data.xml',
        'data/email_template_data.xml',
        'data/cron_data.xml',
        'data/sequence_data.xml',

        'report/occupancy_report.xml',
        'report/report_actions.xml',

        'wizard/occupancy_wizard.xml',
        'wizard/redeem_view.xml',
        'wizard/room_available_wizard.xml',

        'views/room_views.xml',
        'views/guest_views.xml',
        'views/booking_views.xml',
        'views/review_views.xml',
        'views/invoice_views.xml',
        'views/service_views.xml',
        'views/stock_dashboard.xml',
        'views/payment_views.xml',
        'views/menu_views.xml',
        'views/register_page_view.xml',
        'views/loyalty_rewards_views.xml',

    ],

    'demo': [
        'demo/demo_data.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'hotel/static/src/css/*.css',
            'hotel/static/src/xml/*.xml',
            'hotel/static/src/js/*.js',
            'hotel/static/src/html/*.html',
        ],
        'web.assets_frontend': [
            'hotel/static/src/css/*.css',
        ],
    },
}
