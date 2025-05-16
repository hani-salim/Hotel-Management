from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class HotelOccupancyReport(models.AbstractModel):
    _name = 'report.hotel.report_occupancy'
    _description = 'Hotel Occupancy Report'

    # @api.constrains('date_from', 'date_to')
    # def _check_dates(self):
    #     for record in self:
    #         if record.date_from > record.date_to:
    #             raise UserError("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

    def _get_report_values(self, docids, data=None):
        _logger.info("==== بدء تنفيذ الدالة ====")
        try:
            if not data:
                print("تحذير: بيانات الإدخال (data) فارغة!")
                data = {}

            date_from = fields.Date.from_string(data.get('date_from', '')) or fields.Date.today()
            date_to = fields.Date.from_string(data.get('date_to', '')) or fields.Date.today()

            print(f"تاريخ البداية: {date_from} (نوع: {type(date_from)})")
            print(f"تاريخ النهاية: {date_to} (نوع: {type(date_to)})")

            bookings = self.env['hotel.booking'].search([
                ('check_in_date', '<=', date_to),
                ('check_out_date', '>=', date_from),
                ('state', '=', 'confirmed')
            ])
            print(f"عدد الحجوزات المسترجعة: {len(bookings)}")

            rooms = self.env['hotel.room'].search([])
            print(f"عدد الغرف المسترجعة: {len(rooms)}")

            room_data = []
            for room in rooms:
                room_bookings = bookings.filtered(lambda b: b.room_id == room)
                occupied_days = sum(
                    (min(date_to, booking.check_out_date.date()) - max(date_from,
                                                                       booking.check_in_date.date())).days + 1
                    for booking in room_bookings
                )
                total_days = (date_to - date_from).days + 1
                occupancy_rate = (occupied_days / total_days) * 100 if total_days > 0 else 0

                room_data.append({
                    'room': room.name,
                    'floor': room.floor,
                    'occupied_days': occupied_days,
                    'occupancy_rate': round(occupancy_rate, 2)
                })

            print("بيانات الغرف المُعدة:")
            for room in room_data[:5]:  # طباعة أول 5 غرف فقط لتجنب الفوضى
                print(room)

            print("===== انتهاء تنفيذ _get_report_values =====\n\n")

            return {
                'doc_ids': docids,
                'doc_model': 'hotel.room',
                'data': data,
                'rooms': room_data,
                'date_from': data.get('date_from'),
                'date_to': data.get('date_to')
            }

        except Exception as e:
            print(f"حدث خطأ: {str(e)}")
            raise