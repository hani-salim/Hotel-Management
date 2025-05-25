from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class HotelAPI(http.Controller):

    @http.route('/api/hotel/rooms/available', type='json', auth='public', methods=['GET'])
    def get_available_rooms(self, **kwargs):
        try:
            domain = [('is_available', '=', True)]

            if 'floor' in kwargs:
                domain.append(('floor', '=', int(kwargs['floor'])))

            if 'view_type' in kwargs:
                domain.append(('view_type', '=', kwargs['view_type']))

            rooms = request.env['hotel.room'].sudo().search_read(
                domain,
                ['id', 'name', 'floor', 'view_type', 'price_per_night']
            )

            return {'status': 'success', 'rooms': rooms}

        except Exception as e:
            _logger.error("Error: %s", str(e), exc_info=True)
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/hotel/guest_form', type='http', auth='public', website=True)
    def guest_form(self, **kwargs):
        return request.render('hotel.guest_form_template', {
            'error': '',
            'values': {},
        })

    @http.route('/api/hotel/guest_form/submit', type='http', auth='user', methods=['POST'], website=True)
    def guest_form_submit(self, **post):
        _logger.info("guest_form_submit called")
        _logger.info("POST data: %s", post)
        values = post

        if not post.get('name'):
            error = 'اسم الضيف مطلوب.'
            return request.render('hotel.guest_form_template', {'error': error, 'values': values})

        try:
            partner_vals = {
                'name': post.get('name'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'street': post.get('street'),
                'city': post.get('city'),
                'is_company': post.get('is_company') == 'on',
                'company_name': post.get('company_name'),
                'customer_rank': 1,
            }
            country_id = post.get('country_id')
            if country_id:
                partner_vals['country_id'] = int(country_id)
            else:
                partner_vals['country_id'] = False

            partner = request.env['res.partner'].sudo().create(partner_vals)
            _logger.info("Created partner ID: %d", partner.id)

            return request.redirect('/api/hotel/booking_form?partner_id=%d' % partner.id)
        except Exception as e:
            error = "حدث خطأ أثناء إنشاء الضيف: %s" % e
            _logger.error(error)
            return request.render('hotel.guest_form_template', {'error': error, 'values': values})

    @http.route('/api/hotel/booking_form', type='http', auth='public', website=True)
    def booking_form(self, **kwargs):
        partner_id = kwargs.get('partner_id')
        if not partner_id:
            return request.redirect('/api/hotel/guest_form')

        # جلب بيانات الطرف للتأكيد
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if not partner.exists():
            return request.redirect('/api/hotel/guest_form')

        # جلب الغرف المتاحة مثلا
        rooms = request.env['hotel.room'].sudo().search([
            ('is_available', '=', 1)
        ])

        return request.render('hotel.booking_form_template', {
            'partner': partner,
            'rooms': rooms,
            'error': '',
            'values': {},
        })

    @http.route('/api/hotel/booking_form/submit', type='http', auth='public', methods=['POST'], website=True)
    def booking_form_submit(self, **post):
        error = ''
        values = post
        partner_id = post.get('partner_id')

        if not partner_id:
            return request.redirect('/api/hotel/guest_form')

        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if not partner.exists():
            return request.redirect('/api/hotel/guest_form')

        # تحقق من وجود غرف مختارة
        room_ids = []
        if post.get('room_ids'):
            try:
                # التعديل هنا: معالجة قيم room_ids بشكل صحيح
                room_ids_str = post.get('room_ids')
                if room_ids_str:
                    room_ids = [int(room_id) for room_id in room_ids_str.split(',') if room_id.strip()]
            except ValueError as ve:
                error = "تنسيق الغرف غير صحيح"
                _logger.error("ValueError in room_ids: %s", str(ve))

        if not room_ids:
            error = 'يجب اختيار غرفة واحدة على الأقل'
        if not post.get('check_in'):
            error = 'تاريخ الوصول مطلوب.'
        if not post.get('check_out'):
            error = 'تاريخ المغادرة مطلوب.'

        if error:
            rooms = request.env['hotel.room'].sudo().search([('is_available', '=', True)])
            return request.render('hotel.booking_form_template', {
                'partner': partner,
                'rooms': rooms,
                'error': error,
                'values': values,
            })

        try:
            # إنشاء ضيف جديد
            guest_vals = {
                'partner_id': partner.id,
            }
            guest = request.env['hotel.guest'].sudo().create(guest_vals)

            booking_vals = {
                'guest_id': guest.id,
                'room_ids': [(6, 0, room_ids)],  #
                'check_in_date': post.get('check_in'),
                'check_out_date': post.get('check_out'),
                'state': 'draft',
            }
            booking = request.env['hotel.booking'].sudo().create(booking_vals)

            # تحديث حالة جميع الغرف المختارة
            rooms = request.env['hotel.room'].sudo().browse(room_ids)
            rooms.write({
                'state': 'booking',
                'current_guest_id': guest.id,
                'is_available': False  # إضافة هذا الحقل إذا كان موجوداً في النموذج
            })

            return request.render('hotel.booking_success_template', {
                'booking': booking,
                'partner': partner,
            })
        except Exception as e:
            _logger.error("Error creating booking: %s", str(e), exc_info=True)
            rooms = request.env['hotel.room'].sudo().search([('is_available', '=', True)])
            error = "حدث خطأ أثناء إنشاء الحجز: يرجى التحقق من البيانات المدخلة"
            return request.render('hotel.booking_form_template', {
                'partner': partner,
                'rooms': rooms,
                'error': error,
                'values': values,
            })
