/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class ProductComponent extends Component {
    static template = "hotel.ProductComponent";

    setup() {
        this.state = useState({
            products: [],
            loading: true,
            cart: { items: [], total: 0 },
            modal: {
                visible: false,
                product: null,
                quantity: 1,
                total: 0
            },
            showCart: false,
            showConfirmOrder: false,
            orderNotes: "",
            guests: [],
            selectedGuestId: '',
            selectedGuest: null,
            searchTerm: "",
            filteredProducts: [],
            currencySymbol: "$",
            loadError: false
        });

        this.orm = this.env.services.orm;
        this.notification = this.env.services.notification;
        this.user = this.env.services.user;
        this.company = this.env.services.company;

//          onWillUpdateProps(async () => {
//        if (this.state.selectedGuestId) {
//            this.state.selectedGuest = this.state.guests.find(
//                g => g.id === this.state.selectedGuestId
//            );
//        } else {
//            this.state.selectedGuest = null;
//        }
//    });


        onWillStart(async () => {
            await this.loadInitialData();
        });
    }

    async updateSelectedGuest() {
    const guest =await this.state.guests.find(g => g.id === parseInt(this.state.selectedGuestId));
    if (guest) {
        this.state.selectedGuest = guest;
    } else {
        this.state.selectedGuest = null;
        alert("Invalid guest data, please refresh and try again");
    }
}


    async loadInitialData() {
        try {
            // Load currency
            const companies = await this.orm.searchRead(
                "res.company",
                [["id", "=", this.company.currentCompany.id]],
                ["currency_id"]
            );

            if (companies.length > 0 && companies[0].currency_id) {
                const currencies = await this.orm.read(
                    "res.currency",
                    [companies[0].currency_id[0]],
                    ["symbol"]
                );
                this.state.currencySymbol = currencies[0].symbol || "$";
            }

            // Load guests and products
            await this.loadGuests();
            await this.loadProducts();

        } catch (error) {
            console.error("Initialization error:", error);
            this.state.loadError = true;
            this.notification.add("Failed to initialize. Please try again.", { type: "danger" });
        }
    }

    async loadGuests() {
    try {
        const guests = await this.orm.searchRead(
            "hotel.guest",
            [["room_ids", "!=", false]],
            ["id", "partner_id", "room_ids", "check_in_date"],
            { context: { 'load_names': true } }
        );

        if (!guests.length) {
            this.state.guests = [];
            return;
        }

        // جلب تفاصيل الشركاء
        const partnerIds = [...new Set(guests.map(g => g.partner_id[0]))];
        const partners = await this.orm.read(
            "res.partner",
            partnerIds,
            ["name", "email", "phone"]
        );

        // جلب تفاصيل الغرف
        const roomIds = guests.flatMap(g => g.room_ids);
        const rooms = await this.orm.read(
            "hotel.room",
            roomIds,
            ["name", "floor", "view_type"]
        );

        // بناء بيانات الضيوف
        this.state.guests = guests.map(guest => {
            const partner = partners.find(p => p.id === guest.partner_id[0]);
            const guestRooms = rooms.filter(r => guest.room_ids.includes(r.id));

            return {
                id: guest.id,
                partner_id: guest.partner_id,
                partner_name: partner?.name || guest.partner_id[1],
                rooms: guestRooms.map(room => ({
                    id: room.id,
                    name: room.name,
                    floor: room.floor,
                    view_type: room.view_type
                })),
                check_in_date: guest.check_in_date,
                raw_data: guest
            };
        });

    } catch (error) {
        console.error("Failed to load guests:", error);
        this.state.loadError = true;
        this.notification.add("Failed to load guests data. Please refresh.", {
            type: "danger",
            sticky: true
        });
    }
}

    async updateSelectedGuest() {
    const guest = this.state.guests.find(g => g.id === parseInt(this.state.selectedGuestId));
    if (guest) {
        this.state.selectedGuest = guest;
        // عرض جميع غرف الضيف المحدد
        console.log("Selected guest rooms:", guest.rooms);
    } else {
        this.state.selectedGuest = null;
        this.notification.add("Invalid guest selection", { type: "danger" });
    }
}


    async loadProducts() {
        try {
            const products = await this.orm.searchRead(
                "product.product",
                [["sale_ok", "=", true]],
                ["name", "lst_price", "image_1920", "default_code", "taxes_id"]
            );
            this.state.products = products;
            this.state.filteredProducts = [...products];
        } catch (error) {
            console.error("Product loading error:", error);
            this.notification.add("Failed to load products", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    filterProducts() {
        if (!this.state.searchTerm) {
            this.state.filteredProducts = [...this.state.products];
            return;
        }
        const term = this.state.searchTerm.toLowerCase();
        this.state.filteredProducts = this.state.products.filter(product =>
            product.name.toLowerCase().includes(term) ||
            (product.default_code && product.default_code.toLowerCase().includes(term))
        );
    }

    openModal(product) {
        if (!this.state.selectedGuest) {
            this.notification.add("Please select a guest first", { type: "warning" });
            return;
        }
        this.state.modal = {
            visible: true,
            product: product,
            quantity: 1,
            total: product.lst_price
        };
    }

    updateQuantity(event) {
        const qty = parseInt(event.target.value) || 1;
        this.state.modal.quantity = qty;
        this.state.modal.total = this.state.modal.product.lst_price * qty;
    }

    confirmAddToCart() {
        const { product, quantity } = this.state.modal;
        const existingItem = this.state.cart.items.find(item => item.id === product.id);

        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            this.state.cart.items.push({
                ...product,
                quantity: quantity
            });
        }

        this.updateCartTotal();
        this.state.modal.visible = false;
        this.notification.add("Product added to cart", { type: "success" });
    }

    updateCartTotal() {
        this.state.cart.total = this.state.cart.items.reduce(
            (sum, item) => sum + (item.lst_price * item.quantity), 0
        );
    }

    toggleCart() {
        this.state.showCart = !this.state.showCart;
    }

    removeFromCart(productId) {
        this.state.cart.items = this.state.cart.items.filter(item => item.id !== productId);
        this.updateCartTotal();
        this.notification.add("Product removed from cart", { type: "success" });
    }

    confirmOrder() {
    if (this.state.cart.items.length === 0) {
        this.notification.add("Cart is empty", { type: "warning" });
        return;
    }

    if (!this.state.selectedGuest) {
        this.notification.add("Please select a guest first", { type: "warning" });
        return;
    }

    // التحقق من وجود بيانات الضيف الأساسية
    if (!this.state.selectedGuest.partner_id ||
        !this.state.selectedGuest.rooms ||
        this.state.selectedGuest.rooms.length === 0) {
        this.notification.add("Invalid guest data, please refresh and try again", {
            type: "danger",
            buttons: [{
                name: "Refresh Data",
                onClick: () => this.loadInitialData()
            }]
        });
        return;
    }

    // إذا كانت جميع البيانات صحيحة، عرض نافذة التأكيد
    this.state.showConfirmOrder = true;
}


     async finalizeOrder() {
    try {
        // التحقق من وجود ضيف محدد وبياناته
        if (!this.state.selectedGuest || !this.state.selectedGuest.id) {
            this.notification.add("Please select a guest first", { type: "warning" });
            return;
        }

        // تأكيد أن بيانات الضيف كاملة
        if (!this.state.selectedGuest.partner_id || !this.state.selectedGuest.rooms ||
            this.state.selectedGuest.rooms.length === 0) {
            this.notification.add("Invalid guest data, please refresh and try again", {
                type: "danger",
                buttons: [{
                    name: "Refresh Data",
                    onClick: () => this.loadInitialData()
                }]
            });
            return;
        }

        this.state.isProcessing = true;

        // إعداد بيانات الفاتورة
        const invoiceData = {
            move_type: 'out_invoice',
            partner_id: this.state.selectedGuest.partner_id[0],
            guest_id: this.state.selectedGuest.id,
            invoice_origin: `Rooms: ${this.state.selectedGuest.rooms.map(r => r.name).join(', ')}`,
            invoice_line_ids: this.state.cart.items.map(item => [0, 0, {
                product_id: item.id,
                quantity: item.quantity,
                price_unit: item.lst_price,
                name: item.name,
                tax_ids: item.taxes_id || []
            }])
        };

        // البحث عن فاتورة موجودة مرتبطة بغرف الضيف
        const roomIds = this.state.selectedGuest.rooms.map(room => room.id);
        const existingInvoice = await this.orm.searchRead(
            "account.move",
            [
                ["guest_id", "=", this.state.selectedGuest.id],
                ["room_ids", "in", roomIds]
            ],
            ["id"],
            { limit: 1 }
        );

        let invoiceId;
        if (existingInvoice.length) {
            // تحديث الفاتورة الموجودة
            invoiceId = existingInvoice[0].id;

            // الحصول على خطوط الفاتورة الحالية
            const currentLines = await this.orm.read(
                "account.move",
                [invoiceId],
                ["invoice_line_ids"]
            );

            // إضافة الخطوط الجديدة إلى الخطوط الحالية
            invoiceData.invoice_line_ids = [
                ...currentLines[0].invoice_line_ids.map(id => [4, id]),
                ...invoiceData.invoice_line_ids
            ];

            await this.orm.write("account.move", [invoiceId], invoiceData);
        } else {
            // إنشاء فاتورة جديدة
            invoiceId = await this.orm.create("account.move", [invoiceData]);

            // ربط الفاتورة بالغرف
            await this.orm.write(
                "account.move.line",
                invoiceData.invoice_line_ids.map(line => line[2].id),
                { room_id: this.state.selectedGuest.rooms[0].id }
            );
        }

        // عرض إشعار النجاح
        this.notification.add("Products added to guest invoice successfully", {
            type: "success",
            buttons: [{
                name: "View Invoice",
                onClick: () => this.openInvoice(invoiceId)
            }]
        });

        // إعادة تعيين السلة وإغلاق النوافذ
        this.state.cart = { items: [], total: 0 };
        this.state.showCart = false;
        this.state.showConfirmOrder = false;

        // فتح الفاتورة مباشرة
        await this.openInvoice(invoiceId);

    } catch (error) {
        console.error("Checkout error:", error);
        this.notification.add(`Checkout failed: ${error.message}`, {
            type: "danger",
            sticky: true
        });
    } finally {
        this.state.isProcessing = false;
    }
}

async openInvoice(invoiceId) {
    this.env.services.action.doAction({
        type: 'ir.actions.act_window',
        name: 'Guest Invoice',
        res_model: 'account.move',
        res_id: invoiceId,
        views: [[false, 'form']],
        target: 'current',
        context: {
            form_view_initial_mode: 'edit',
            create: false
        }
    });
}
}

registry.category("actions").add("hotel.products_component", ProductComponent);