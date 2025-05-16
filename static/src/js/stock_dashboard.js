odoo.define('hotel.stock_dashboard', function (require) {
    "use strict";

    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                // تلوين البطاقة حسب الفئة
                if (self.recordData.product_categ_id) {
                    var categoryId = self.recordData.product_categ_id.res_id;
                    var color = self.kanban_getcolor(categoryId) || '#875A7B';
                    self.$el.find('.stock-card').css({
                        'border-left': '4px solid ' + color,
                        'box-shadow': '0 2px 5px rgba(0,0,0,0.1)'
                    });
                    self.$el.find('.category-badge').css({
                        'background-color': color,
                        'color': 'white',
                        'padding': '3px 8px',
                        'border-radius': '12px',
                        'font-size': '12px'
                    });
                }

                // تنسيق الكمية (أحمر إذا كانت أقل من 10)
                var quantity = self.recordData.quantity.value;
                var $h2 = self.$el.find('h2');
                if (quantity < 10) {
                    $h2.addClass('text-danger').removeClass('text-success');
                } else {
                    $h2.addClass('text-success').removeClass('text-danger');
                }

                // تنسيق اسم المنتج في الـ Header والـ Location
                self.$el.find('.product-name, .product-name-location').css({
                    'font-weight': '600',
                    'font-size': '14px',
                    'color': '#333',
                    'margin': '5px 0'
                });

                // تأثيرات الـ Hover
                self.$el.hover(
                    function() {
                        $(this).find('.stock-card').css('transform', 'translateY(-3px)');
                    },
                    function() {
                        $(this).find('.stock-card').css('transform', 'translateY(0)');
                    }
                );
            });
        }
    });
});