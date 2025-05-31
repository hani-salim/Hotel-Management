# occupancy_report.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HotelOccupancyReport(models.AbstractModel):
    _name = 'report.hotel.report_occupancy'
    _description = 'Hotel Occupancy Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        try:
            _logger.info("Starting occupancy report generation")

            if not data:
                data = {}
                _logger.warning("No data provided, using default values")

            # التحقق من صحة التواريخ
            date_from = fields.Date.from_string(data.get('date_from')) or fields.Date.today()
            date_to = fields.Date.from_string(data.get('date_to')) or fields.Date.today()

            if date_from > date_to:
                raise UserError(_("تاريخ النهاية يجب أن يكون بعد تاريخ البداية"))

            _logger.info(f"Generating report from {date_from} to {date_to}")

            # الحصول على البيانات
            bookings = self.env['hotel.booking'].search([
                ('check_in_date', '<=', date_to),
                ('check_out_date', '>=', date_from),
                ('state', '=', 'confirm')
            ])

            rooms = self.env['hotel.room'].search([])

            if not rooms:
                raise UserError(_("لا توجد غرف متاحة في النظام"))

            room_data = []
            for room in rooms:
                try:
                    room_bookings = bookings.filtered(lambda b: room in b.room_ids)

                    occupied_days = 0
                    for booking in room_bookings:
                        start = max(date_from, booking.check_in_date.date())
                        end = min(date_to, booking.check_out_date.date())
                        occupied_days += (end - start).days + 1

                    total_days = (date_to - date_from).days + 1
                    occupancy_rate = (occupied_days / total_days) * 100 if total_days > 0 else 0

                    room_data.append({
                        'room': room.name or '',
                        'floor': room.floor or 0,
                        'view_type': dict(room._fields['view_type'].selection).get(room.view_type, ''),
                        'occupied_days': occupied_days,
                        'occupancy_rate': round(occupancy_rate, 2),
                        'status': dict(room._fields['state'].selection).get(room.state, ''),
                        'price_per_night': room.price_per_night or 0
                    })
                except Exception as e:
                    _logger.error(f"Error processing room {room.id}: {str(e)}")
                    continue

            # حساب الإجماليات
            total_rooms = len(rooms)
            total_occupied_days = sum(r['occupied_days'] for r in room_data)
            avg_occupancy = sum(r['occupancy_rate'] for r in room_data) / total_rooms if total_rooms > 0 else 0

            return {
                'doc_ids': docids,
                'doc_model': 'hotel.room',
                'data': data,
                'rooms': room_data,
                'date_from': date_from,
                'date_to': date_to,
                'total_rooms': total_rooms,
                'total_occupied_days': total_occupied_days,
                'avg_occupancy_rate': round(avg_occupancy, 2)
            }

        except UserError as e:
            _logger.error(f"UserError in report: {str(e)}")
            raise
        except Exception as e:
            _logger.error(f"Unexpected error in report generation: {str(e)}", exc_info=True)
            raise UserError(_("حدث خطأ غير متوقع أثناء إنشاء التقرير. الرجاء التحقق من السجلات."))