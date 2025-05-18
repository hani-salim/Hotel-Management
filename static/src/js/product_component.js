/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";

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
            loadError: false,
            isProcessing: false,
            isProcessingInvoice: false,
            loyaltyDiscount: 0,
            loyaltyReward: null,
            loyaltyPointsUsed: 0,
        });

        this.orm = this.env.services.orm;
        this.notification = this.env.services.notification;
        this.user = this.env.services.user;
        this.company = this.env.services.company;

            onWillStart(async () => {
            await this.loadInitialData();
        });
    }

    // دالة مساعدة لحساب السعر بعد الخصم
    getDiscountedPrice(price, discount) {
        return price * (1 - (discount || 0) / 100);
    }

    // دالة مساعدة لتنسيق السعر
    formatPrice(price) {
        return this.state.currencySymbol + price.toFixed(2);
    }

    async updateSelectedGuest() {
        const guest = this.state.guests.find(g => g.id === parseInt(this.state.selectedGuestId));
        if (guest) {
            this.state.selectedGuest = guest;
            this.state.loyaltyDiscount = 0;
            this.state.loyaltyReward = null;
            this.state.loyaltyPointsUsed = 0;
        } else {
            this.state.selectedGuest = null;
            this.state.loyaltyDiscount = 0;
            this.state.loyaltyReward = null;
            this.state.loyaltyPointsUsed = 0;
            this.notification.add("Invalid guest data, please refresh and try again", { type: "danger" });
        }
    }

    async loadInitialData() {
        try {
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
                ["id", "partner_id", "room_ids", "check_in_date", "loyalty_points"],
                { context: { 'load_names': true } }
            );

            if (!guests.length) {
                this.state.guests = [];
                return;
            }

            const partnerIds = [...new Set(guests.map(g => g.partner_id[0]))];
            const partners = await this.orm.read(
                "res.partner",
                partnerIds,
                ["name", "email", "phone"]
            );

            const roomIds = guests.flatMap(g => g.room_ids);
            const rooms = await this.orm.read(
                "hotel.room",
                roomIds,
                ["name", "floor", "view_type"]
            );

            this.state.guests = guests.map(guest => ({
                id: guest.id,
                partner_id: guest.partner_id,
                partner_name: partners.find(p => p.id === guest.partner_id[0])?.name || guest.partner_id[1],
                rooms: rooms.filter(r => guest.room_ids.includes(r.id)).map(room => ({
                    id: room.id,
                    name: room.name,
                    floor: room.floor,
                    view_type: room.view_type
                })),
                check_in_date: guest.check_in_date,
                loyalty_points: guest.loyalty_points || 0,
                raw_data: guest
            }));

        } catch (error) {
            console.error("Failed to load guests:", error);
            this.state.loadError = true;
            this.notification.add("Failed to load guests data. Please refresh.", {
                type: "danger",
                sticky: true
            });
        }
    }

    async loadProducts() {
        try {
            const products = await this.orm.searchRead(
                "product.product",
                [["sale_ok", "=", true], ["type", "=", "product"]],
                ["name", "lst_price", "image_1920", "default_code", "taxes_id", "free_qty", "qty_available"]
            );

            this.state.products = products.map(product => ({
                ...product,
                free_qty: product.free_qty || product.qty_available || 0,
                availableQty: product.free_qty || product.qty_available || 0,
                lowStock: (product.free_qty || product.qty_available || 0) < 5
            }));

            this.state.filteredProducts = [...this.state.products];
        } catch (error) {
            console.error("Product loading error:", error);
            this.notification.add("Failed to load products", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async openModal(product) {
        if (!this.state.selectedGuest) {
            this.notification.add("Please select a guest first", { type: "warning" });
            return;
        }

        const currentProduct = await this.orm.read(
            "product.product",
            [product.id],
            ["free_qty", "qty_available"]
        );

        const availableQty = currentProduct[0].free_qty || currentProduct[0].qty_available || 0;

        if (availableQty <= 0) {
            this.notification.add("This product is currently out of stock", {
                type: "danger",
                buttons: [{
                    name: "Refresh Stock",
                    onClick: async () => {
                        await this.loadProducts();
                        this.openModal(product);
                    }
                }]
            });
            return;
        }

        const existingInCart = this.state.cart.items.find(item => item.id === product.id);
        const cartQty = existingInCart ? existingInCart.quantity : 0;
        const actuallyAvailable = Math.max(0, availableQty - cartQty);

        this.state.modal = {
            visible: true,
            product: product,
            quantity: 1,
            total: product.lst_price,
            maxQty: actuallyAvailable,
            availableQty: availableQty
        };
    }

    updateQuantity(event) {
        const qty = parseInt(event.target.value) || 1;
        const maxQty = this.state.modal.maxQty;

        if (qty > maxQty) {
            this.notification.add(`Maximum available quantity is ${maxQty}`, { type: "warning" });
            this.state.modal.quantity = maxQty;
        } else if (qty < 1) {
            this.state.modal.quantity = 1;
        } else {
            this.state.modal.quantity = qty;
        }

        this.state.modal.total = this.state.modal.product.lst_price * this.state.modal.quantity;
    }

    confirmAddToCart() {
        const { product, quantity } = this.state.modal;

        if (!product || !product.id) {
            this.notification.add("Invalid product data", { type: "danger" });
            return;
        }

        if (quantity <= 0) {
            this.notification.add("Quantity must be at least 1", { type: "warning" });
            return;
        }

        const availableQty = product.free_qty || 0;

        if (availableQty < quantity) {
            this.notification.add(
                `Cannot add ${quantity} items. Only ${availableQty} available in stock`,
                { type: "danger" }
            );
            return;
        }

        const existingItem = this.state.cart.items.find(item => item.id === product.id);
        const alreadyInCart = existingItem ? existingItem.quantity : 0;
        const totalRequested = alreadyInCart + quantity;

        if (availableQty < totalRequested) {
            this.notification.add(
                `Cannot add more items. Only ${availableQty - alreadyInCart} additional available in stock`,
                { type: "danger" }
            );
            return;
        }

        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            this.state.cart.items.push({
                ...product,
                quantity: quantity,
                discount: 0 // Initialize discount for new items
            });
        }

        this.updateCartTotal();
        this.state.modal.visible = false;
        this.notification.add("Product added to cart", { type: "success" });
    }

    updateCartTotal() {
        this.state.cart.total = this.state.cart.items.reduce(
            (sum, item) => sum + this.getDiscountedPrice(item.lst_price, item.discount) * item.quantity, 0
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

        this.state.showConfirmOrder = true;
    }

    async openPicking(pickingId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Inventory Transfer',
            res_model: 'stock.picking',
            res_id: pickingId,
            views: [[false, 'form']],
            target: 'current'
        });
    }

      async applyLoyaltyDiscount() {
        if (!this.state.selectedGuest) {
            this.notification.add("Please select a guest first", { type: "warning" });
            return;
        }

        try {
            const rewardModel = await this.orm.searchRead(
                "loyalty.reward",
                [["reward_type", "=", "discount"], ["active", "=", true]],
                ["id", "discount_percent", "points_cost"],
                { limit: 1 }
            );

            if (!rewardModel.length) {
                this.notification.add("No active discount reward found", { type: "danger" });
                return;
            }

            const reward = rewardModel[0];
            let remainingPoints = this.state.selectedGuest.loyalty_points;

            this.state.cart.items.forEach(item => {
                if (remainingPoints >= reward.points_cost) {
                    item.discount = reward.discount_percent;
                    remainingPoints -= reward.points_cost;
                } else {
                    item.discount = 0;
                }
            });

            this.state.loyaltyPointsUsed = this.state.selectedGuest.loyalty_points - remainingPoints;
            this.state.loyaltyReward = { id: reward.id };
            this.updateCartTotal();

            this.notification.add(
                `Applied ${reward.discount_percent}% discount (used ${this.state.loyaltyPointsUsed} points)`,
                { type: "success" }
            );

        } catch (error) {
            console.error("Error applying loyalty discount:", error);
            this.notification.add("Failed to apply loyalty discount", { type: "danger" });
        }
    }

    async finalizeOrder() {
        try {
            this.state.isProcessing = true;
            this.state.isProcessingInvoice = true;

            if (!this.state.selectedGuest?.id) {
                throw new Error("Please select a guest first");
            }

            if (this.state.cart.items.length === 0) {
                throw new Error("Cart is empty, cannot complete order");
            }

            await this.loadProducts();

            const stockIssues = [];
            await Promise.all(this.state.cart.items.map(async (item) => {
                const [product] = await this.orm.read(
                    "product.product",
                    [item.id],
                    ["free_qty", "qty_available"]
                );

                const available = product.free_qty || product.qty_available || 0;
                if (available < item.quantity) {
                    stockIssues.push({
                        product: item.name,
                        available,
                        requested: item.quantity
                    });
                }
            }));

            if (stockIssues.length > 0) {
                const messages = stockIssues.map(i =>
                    `${i.product}: Available ${i.available} - Requested ${i.requested}`
                ).join("<br>");

                this.notification.add(`Stock issues:<br>${messages}`, {
                    type: "danger",
                    sticky: true
                });
                return;
            }

            const orderOrigin = `Hotel Order ${new Date().toISOString()} for ${this.state.selectedGuest.partner_name}`;
            const orderData = {
                partner_id: this.state.selectedGuest.partner_id[0],
                order_line: this.state.cart.items.map(item => [0, 0, {
                    product_id: item.id,
                    product_uom_qty: item.quantity,
                    price_unit: item.lst_price,
                    tax_id: item.taxes_id || [],
                    name: item.name,
                    discount: item.discount || 0,
                }]),
                origin: orderOrigin,
                guest_id: this.state.selectedGuest.id,
                note: this.state.orderNotes,
                loyalty_reward_id: this.state.loyaltyReward?.id || false,
                loyalty_points_used: this.state.loyaltyPointsUsed || 0
            };

            const orderId = await this.orm.create("sale.order", [orderData]);
            await this.orm.call("sale.order", "action_confirm", [[orderId]]);


             if (this.state.loyaltyPointsUsed > 0) {
            await this.orm.create("loyalty.transaction", [{
                guest_id: this.state.selectedGuest.id,
                points: -this.state.loyaltyPointsUsed,
                transaction_type: "redeem",
                reward_id: this.state.loyaltyReward?.id || false,
                discount_amount: this.state.loyaltyDiscount,
                description: `Redeemed ${this.state.loyaltyPointsUsed} points for order ${orderId}`,
                reference: `sale.order,${orderId}`
            }]);}

            if (this.state.loyaltyPointsUsed > 0) {
                await this.orm.call(
                    "hotel.guest",
                    "write",
                    [[this.state.selectedGuest.id], {
                        loyalty_points: this.state.selectedGuest.loyalty_points - this.state.loyaltyPointsUsed
                    }]
                );
            }

            const pickingData = await this.orm.searchRead(
                "stock.picking",
                [["sale_id", "=", orderId]],
                ["id", "state"],
                { limit: 1 }
            );

            if (pickingData.length > 0) {
                try {
                    const result = await this.orm.call(
                        "stock.picking",
                        "button_validate",
                        [[pickingData[0].id]]
                    );

                    if (result && result.res_id) {
                        this.notification.add("Please complete additional validation steps", {
                            type: "warning",
                            buttons: [{
                                name: "Complete Validation",
                                onClick: () => this.openPicking(result.res_id)
                            }]
                        });
                    }

                    await new Promise(resolve => setTimeout(resolve, 1500));
                    await this.loadProducts();
                } catch (validateError) {
                    console.error("Picking validation error:", validateError);
                    this.notification.add("Inventory update requires additional steps", {
                        type: "warning",
                        buttons: [{
                            name: "Complete Inventory",
                            onClick: () => this.openPicking(pickingData[0].id)
                        }]
                    });
                }
            }

            const draftInvoices = await this.orm.searchRead(
                "account.move",
                [
                    ["guest_id", "=", this.state.selectedGuest.id],
                    ["state", "=", "draft"],
                    ["move_type", "=", "out_invoice"]
                ],
                ["id"],
                { limit: 1 }
            );

            let invoiceId;
            if (draftInvoices.length > 0) {
                invoiceId = draftInvoices[0].id;
                await this.orm.call(
                    "account.move",
                    "write",
                    [[invoiceId], {
                        invoice_line_ids: this.state.cart.items.map(item => [0, 0, {
                            product_id: item.id,
                            quantity: item.quantity,
                            price_unit: item.lst_price,
                            name: item.name,
                            tax_ids: item.taxes_id || [],
                            discount: item.discount || 0
                        }])
                    }]
                );
                this.notification.add("Products added to existing draft invoice", { type: "success" });
            } else {
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
                        tax_ids: item.taxes_id || [],
                        discount: item.discount || 0
                    }])
                };
                invoiceId = await this.orm.create("account.move", [invoiceData]);
                this.notification.add("New invoice created", { type: "success" });
            }



            this.notification.add("Order processed successfully", {
                type: "success",
                buttons: [
                    {
                        name: "View Invoice",
                        onClick: () => this.openInvoice(invoiceId)
                    },
                    {
                        name: "View Order",
                        onClick: () => this.openOrder(orderId)
                    },
                    ...(pickingData.length > 0 ? [{
                        name: "View Inventory",
                        onClick: () => this.openPicking(pickingData[0].id)
                    }] : [])
                ]
            });

            this.resetCart();

        } catch (error) {
            console.error("Failed to complete order:", error);
            this.notification.add(`Failed to complete order: ${error.message}`, {
                type: "danger",
                sticky: true,
                buttons: [{
                    name: "Retry",
                    onClick: () => this.finalizeOrder()
                }]
            });
        } finally {
            this.state.isProcessing = false;
            this.state.isProcessingInvoice = false;
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

    async openOrder(orderId) {
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sale Order',
            res_model: 'sale.order',
            res_id: orderId,
            views: [[false, 'form']],
            target: 'current'
        });
    }

    resetCart() {
        this.state.cart = { items: [], total: 0 };
        this.state.showCart = false;
        this.state.showConfirmOrder = false;
        this.state.modal.visible = false;
        this.state.orderNotes = "";
        this.state.loyaltyDiscount = 0;
        this.state.loyaltyReward = null;
        this.state.loyaltyPointsUsed = 0;
    }
}

registry.category("actions").add("hotel.product_component", ProductComponent);