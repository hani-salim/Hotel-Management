odoo.define('hotel.stock_dashboard', function (require) {
    "use strict";

    var KanbanRecord = require('web.KanbanRecord');
    var registry = require('web.registry');

    var HotelKanbanCard = KanbanRecord.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {

                // جدول الألوان حسب الفئة
                var colorMap = {
                    1: '#e74c3c',
                    2: '#f39c12',
                    3: '#27ae60',
                    4: '#2980b9'
                };

                if (self.recordData.product_categ_id) {
                    var categoryId = self.recordData.product_categ_id.res_id;
                    var color = colorMap[categoryId] || '#875A7B';

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

                // تنسيق الكمية
                var quantity = parseFloat(self.recordData.quantity.value);
                var $h2 = self.$el.find('h2');
                if (!isNaN(quantity)) {
                    $h2.removeClass('text-danger text-success');
                    if (quantity < 10) {
                        $h2.addClass('text-danger');
                    } else {
                        $h2.addClass('text-success');
                    }
                }

                // تنسيق اسم المنتج
                self.$el.find('.product-name, .product-name-location').css({
                    'font-weight': '600',
                    'font-size': '14px',
                    'color': '#333',
                    'margin': '5px 0'
                });

                // تأثير hover
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

    registry.get('kanban_record').add('hotel_kanban_card', HotelKanbanCard);
});