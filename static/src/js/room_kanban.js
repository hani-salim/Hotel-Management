odoo.define('hotel.room_kanban', function (require) {
    "use strict";

    var KanbanController = require('web.KanbanController');

    KanbanController.include({
        willStart: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                // إضافة تأكيد تحميل الأزرار
                console.log('Kanban Controller Loaded for hotel.room');
            });
        },

        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.modelName === 'hotel.room') {
                // إنشاء زرين احتياطيين كحل أخير
                var $buttons = $(`
                    <div class="js_fallback_buttons" style="padding:15px; background:#f8f9fa; margin-bottom:20px; display:flex; gap:15px;">
                        <button class="btn btn-primary" id="custom_check_availability">
                            <i class="fa fa-calendar-check"></i> Check Availability (JS)
                        </button>
                        <button class="btn btn-secondary" id="custom_show_dashboard">
                            <i class="fa fa-tachometer-alt"></i> Dashboard (JS)
                        </button>
                    </div>
                `);

                $buttons.find('#custom_check_availability').click(this._onCustomCheckAvailability.bind(this));
                $buttons.find('#custom_show_dashboard').click(this._onCustomShowDashboard.bind(this));

                $node.prepend($buttons);
            }
        },

        _onCustomCheckAvailability: function() {
            this.do_action({
                type: 'ir.actions.act_window',
                name: 'Check Availability',
                res_model: 'hotel.room.availability.wizard',
                view_mode: 'form',
                target: 'new',
                views: [[false, 'form']],
            });
        },

        _onCustomShowDashboard: function() {
            this.do_action({
                type: 'ir.actions.act_window',
                name: 'All Rooms',
                res_model: 'hotel.room',
                view_mode: 'kanban,tree,form',
                target: 'current',
            });
        }
    });
});