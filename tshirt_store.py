#!/usr/bin/env python3
"""
Single-file T-shirt shop website.

What it does:
- Serves a responsive storefront at http://localhost:8000
- Displays products from an in-memory catalog
- Lets users add items to a cart in the browser
- Accepts checkout form submissions
- Saves orders to orders.json on the server

Run:
    python3 tshirt_store.py

Then open:
    http://localhost:8000
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8000
STORE_NAME = "ThreadHaus"
CURRENCY_SYMBOL = "$"
ORDERS_FILE = Path(__file__).with_name("orders.json")

PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "classic-black-tee",
        "name": "Classic Black Tee",
        "price": "24.99",
        "tag": "Best seller",
        "color": "Black",
        "sizes": ["S", "M", "L", "XL"],
        "description": "Soft everyday cotton tee with a clean streetwear fit.",
        "gradient": "linear-gradient(135deg, #111827, #374151)",
    },
    {
        "id": "sunset-vintage-tee",
        "name": "Sunset Vintage Tee",
        "price": "29.99",
        "tag": "New drop",
        "color": "Rust",
        "sizes": ["S", "M", "L"],
        "description": "Vintage-washed shirt with a warm sunset-inspired palette.",
        "gradient": "linear-gradient(135deg, #ea580c, #f59e0b)",
    },
    {
        "id": "minimal-white-tee",
        "name": "Minimal White Tee",
        "price": "22.99",
        "tag": "Essentials",
        "color": "White",
        "sizes": ["XS", "S", "M", "L", "XL"],
        "description": "Clean premium staple with a modern cut and soft finish.",
        "gradient": "linear-gradient(135deg, #e5e7eb, #9ca3af)",
    },
    {
        "id": "midnight-oversized-tee",
        "name": "Midnight Oversized Tee",
        "price": "34.99",
        "tag": "Oversized fit",
        "color": "Navy",
        "sizes": ["M", "L", "XL", "XXL"],
        "description": "Heavyweight oversized tee built for comfort and layered looks.",
        "gradient": "linear-gradient(135deg, #1d4ed8, #312e81)",
    },
]

INDEX_HTML = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{STORE_NAME} | Premium T-Shirts</title>
  <style>
    :root {{
      --bg: #0b1020;
      --panel: #121935;
      --card: #171f45;
      --soft: #a7b0d6;
      --text: #f5f7ff;
      --accent: #7c3aed;
      --accent-2: #22c55e;
      --danger: #ef4444;
      --border: rgba(255,255,255,0.08);
      --shadow: 0 20px 50px rgba(0,0,0,0.35);
      --radius: 18px;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(124,58,237,0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(34,197,94,0.14), transparent 20%),
        linear-gradient(180deg, #070b17, var(--bg));
      min-height: 100vh;
    }}

    a {{ color: inherit; text-decoration: none; }}
    button, input, textarea, select {{ font: inherit; }}

    .container {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; }}

    .topbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      backdrop-filter: blur(14px);
      background: rgba(8, 12, 24, 0.72);
      border-bottom: 1px solid var(--border);
    }}

    .nav {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 0;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 800;
      letter-spacing: 0.3px;
    }}

    .logo {{
      width: 38px;
      height: 38px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, var(--accent), #2563eb);
      box-shadow: var(--shadow);
      font-weight: 900;
    }}

    .nav-actions {{ display: flex; gap: 12px; align-items: center; }}

    .pill {{
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-radius: 999px;
      color: var(--soft);
      background: rgba(255,255,255,0.03);
    }}

    .cart-button {{
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      background: linear-gradient(135deg, var(--accent), #5b21b6);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }}

    .hero {{
      padding: 56px 0 28px;
      display: grid;
      gap: 28px;
      grid-template-columns: 1.15fr 0.85fr;
      align-items: center;
    }}

    .hero-card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      border: 1px solid var(--border);
      border-radius: 26px;
      box-shadow: var(--shadow);
    }}

    .hero-copy {{ padding: 34px; }}

    .eyebrow {{
      display: inline-flex;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(124,58,237,0.16);
      color: #d7c7ff;
      font-size: 14px;
      margin-bottom: 18px;
      border: 1px solid rgba(124,58,237,0.24);
    }}

    h1 {{
      margin: 0 0 12px;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 1;
      letter-spacing: -1.4px;
    }}

    .hero p {{
      color: var(--soft);
      font-size: 18px;
      line-height: 1.6;
      margin: 0 0 24px;
      max-width: 60ch;
    }}

    .hero-cta {{ display: flex; flex-wrap: wrap; gap: 12px; }}

    .primary, .secondary {{
      border: 0;
      padding: 14px 18px;
      border-radius: 14px;
      cursor: pointer;
      font-weight: 700;
    }}

    .primary {{
      background: linear-gradient(135deg, var(--accent), #5b21b6);
      color: white;
    }}

    .secondary {{
      background: rgba(255,255,255,0.05);
      color: var(--text);
      border: 1px solid var(--border);
    }}

    .hero-visual {{
      min-height: 390px;
      padding: 20px;
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}

    .visual-tile {{
      border-radius: 20px;
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(255,255,255,0.07);
      min-height: 170px;
    }}

    .visual-tile::after {{
      content: "";
      position: absolute;
      inset: auto -15% -25% auto;
      width: 120px;
      height: 120px;
      border-radius: 50%;
      background: rgba(255,255,255,0.10);
      filter: blur(10px);
    }}

    .visual-label {{
      position: absolute;
      left: 14px;
      bottom: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(10,12,24,0.45);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,0.10);
      font-weight: 700;
      font-size: 14px;
    }}

    .section-head {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 12px;
      margin: 24px 0 16px;
    }}

    .section-head h2 {{ margin: 0; font-size: 28px; }}
    .section-head p {{ margin: 0; color: var(--soft); }}

    .catalog {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
      padding-bottom: 34px;
    }}

    .card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      box-shadow: var(--shadow);
    }}

    .product-art {{
      height: 210px;
      position: relative;
    }}

    .product-art::before {{
      content: "";
      position: absolute;
      inset: 22px;
      border-radius: 24px 24px 50px 50px;
      background: rgba(255,255,255,0.14);
      transform: perspective(500px) rotateX(12deg);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16);
    }}

    .tag {{
      position: absolute;
      top: 14px;
      left: 14px;
      padding: 8px 10px;
      border-radius: 999px;
      background: rgba(10,12,24,0.45);
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,0.12);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.2px;
    }}

    .card-body {{ padding: 18px; }}

    .title-row {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
    }}

    .title-row h3 {{ margin: 0; font-size: 20px; }}
    .price {{ font-weight: 900; font-size: 20px; white-space: nowrap; }}

    .muted {{ color: var(--soft); }}
    .sizes {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }}

    .size-chip {{
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.04);
      border: 1px solid var(--border);
      color: var(--soft);
      font-size: 13px;
      font-weight: 700;
    }}

    .card-actions {{ display: flex; gap: 10px; align-items: center; }}

    .size-select {{
      flex: 1;
      min-width: 0;
      padding: 12px 14px;
      background: rgba(255,255,255,0.04);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 12px;
    }}

    .add-button {{
      padding: 12px 14px;
      border-radius: 12px;
      border: 0;
      background: linear-gradient(135deg, var(--accent-2), #15803d);
      color: white;
      font-weight: 800;
      cursor: pointer;
      white-space: nowrap;
    }}

    .content-grid {{
      display: grid;
      grid-template-columns: 1fr 370px;
      gap: 20px;
      align-items: start;
      padding-bottom: 50px;
    }}

    .checkout-panel {{
      position: sticky;
      top: 88px;
      padding: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }}

    .cart-items {{ display: grid; gap: 12px; margin: 16px 0 18px; }}

    .cart-item {{
      padding: 12px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.03);
      display: grid;
      gap: 6px;
    }}

    .cart-line {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
    }}

    .tiny {{ font-size: 13px; color: var(--soft); }}
    .danger-link {{
      border: 0;
      background: transparent;
      color: #fca5a5;
      cursor: pointer;
      padding: 0;
      font-weight: 700;
    }}

    .summary {{
      padding: 14px 0;
      display: grid;
      gap: 10px;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      margin-bottom: 18px;
    }}

    .summary-row {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }}

    .summary-row.total {{ font-size: 20px; font-weight: 900; }}

    form.checkout {{ display: grid; gap: 12px; }}

    .field {{ display: grid; gap: 7px; }}
    .field label {{ font-size: 14px; color: var(--soft); font-weight: 700; }}

    .field input, .field textarea {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      padding: 13px 14px;
      resize: vertical;
    }}

    .field input::placeholder,
    .field textarea::placeholder {{ color: #7f89b5; }}

    .checkout-submit {{
      margin-top: 6px;
      border: 0;
      border-radius: 14px;
      padding: 15px 18px;
      background: linear-gradient(135deg, var(--accent), #4f46e5);
      color: white;
      font-weight: 800;
      cursor: pointer;
    }}

    .notice {{
      margin-top: 12px;
      padding: 13px 14px;
      border-radius: 14px;
      display: none;
      white-space: pre-wrap;
      line-height: 1.5;
    }}

    .notice.success {{
      display: block;
      background: rgba(34,197,94,0.12);
      color: #bbf7d0;
      border: 1px solid rgba(34,197,94,0.25);
    }}

    .notice.error {{
      display: block;
      background: rgba(239,68,68,0.12);
      color: #fecaca;
      border: 1px solid rgba(239,68,68,0.25);
    }}

    footer {{
      padding: 26px 0 48px;
      color: var(--soft);
      text-align: center;
    }}

    @media (max-width: 1080px) {{
      .catalog {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .hero {{ grid-template-columns: 1fr; }}
      .content-grid {{ grid-template-columns: 1fr; }}
      .checkout-panel {{ position: static; }}
    }}

    @media (max-width: 680px) {{
      .catalog {{ grid-template-columns: 1fr; }}
      .hero-copy {{ padding: 24px; }}
      .hero-visual {{ min-height: auto; }}
      .nav {{ align-items: start; flex-direction: column; }}
      .nav-actions {{ width: 100%; justify-content: space-between; }}
      .card-actions {{ flex-direction: column; }}
      .size-select, .add-button {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="container nav">
      <a class="brand" href="#top">
        <div class="logo">T</div>
        <div>
          <div>{STORE_NAME}</div>
          <div class="tiny">Premium T-shirt storefront</div>
        </div>
      </a>
      <div class="nav-actions">
        <a class="pill" href="#shop">Shop</a>
        <a class="pill" href="#checkout">Checkout</a>
        <button class="cart-button" id="cartButton">Cart (<span id="cartCount">0</span>)</button>
      </div>
    </div>
  </div>

  <main class="container" id="top">
    <section class="hero">
      <div class="hero-card hero-copy">
        <div class="eyebrow">Built as a single-file shop you can run locally</div>
        <h1>Sell premium T-shirts with a clean storefront.</h1>
        <p>
          This demo shop includes product cards, a working cart, checkout form,
          and server-side order saving. Replace the product list with your own
          designs and connect a payment provider when you are ready to go live.
        </p>
        <div class="hero-cta">
          <a class="primary" href="#shop">Browse the collection</a>
          <a class="secondary" href="#checkout">Jump to checkout</a>
        </div>
      </div>

      <div class="hero-card hero-visual" aria-hidden="true">
        <div class="visual-tile" style="background: linear-gradient(135deg, #7c3aed, #2563eb);">
          <div class="visual-label">Graphic drop</div>
        </div>
        <div class="visual-tile" style="background: linear-gradient(135deg, #f97316, #ef4444);">
          <div class="visual-label">Vintage wash</div>
        </div>
        <div class="visual-tile" style="background: linear-gradient(135deg, #111827, #374151);">
          <div class="visual-label">Core essentials</div>
        </div>
        <div class="visual-tile" style="background: linear-gradient(135deg, #16a34a, #0f766e);">
          <div class="visual-label">Limited colors</div>
        </div>
      </div>
    </section>

    <div class="content-grid">
      <section id="shop">
        <div class="section-head">
          <div>
            <h2>Featured T-shirts</h2>
            <p>Editable product catalog served by the Python script.</p>
          </div>
        </div>
        <div class="catalog" id="catalog"></div>
      </section>

      <aside class="checkout-panel" id="checkout">
        <h2 style="margin-top:0;">Cart & checkout</h2>
        <p class="muted">Orders are saved to <code>orders.json</code> on the server.</p>

        <div class="cart-items" id="cartItems"></div>

        <div class="summary">
          <div class="summary-row"><span>Subtotal</span><strong id="subtotal">{CURRENCY_SYMBOL}0.00</strong></div>
          <div class="summary-row"><span>Shipping</span><strong id="shipping">{CURRENCY_SYMBOL}6.00</strong></div>
          <div class="summary-row total"><span>Total</span><strong id="total">{CURRENCY_SYMBOL}6.00</strong></div>
        </div>

        <form class="checkout" id="checkoutForm">
          <div class="field">
            <label for="name">Full name</label>
            <input id="name" name="name" placeholder="Alex Rivera" required>
          </div>

          <div class="field">
            <label for="email">Email</label>
            <input id="email" name="email" type="email" placeholder="alex@example.com" required>
          </div>

          <div class="field">
            <label for="address">Shipping address</label>
            <textarea id="address" name="address" rows="4" placeholder="123 Main Street, City, Country" required></textarea>
          </div>

          <button class="checkout-submit" type="submit">Place order</button>
          <div class="notice" id="notice"></div>
        </form>
      </aside>
    </div>
  </main>

  <footer>
    {STORE_NAME} demo store. Built with one Python file, ready for your catalog and payment integration.
  </footer>

  <script>
    const currencySymbol = {json.dumps(CURRENCY_SYMBOL)};
    const flatShipping = 6.00;
    let products = [];
    let cart = loadCart();

    async function init() {{
      products = await fetch('/api/products').then(r => r.json());
      renderCatalog();
      renderCart();
      document.getElementById('checkoutForm').addEventListener('submit', submitOrder);
      document.getElementById('cartButton').addEventListener('click', () => {{
        document.getElementById('checkout').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});
    }}

    function loadCart() {{
      try {{
        const raw = localStorage.getItem('tshirt_store_cart');
        return raw ? JSON.parse(raw) : [];
      }} catch (_) {{
        return [];
      }}
    }}

    function saveCart() {{
      localStorage.setItem('tshirt_store_cart', JSON.stringify(cart));
    }}

    function money(value) {{
      return currencySymbol + Number(value).toFixed(2);
    }}

    function renderCatalog() {{
      const catalog = document.getElementById('catalog');
      catalog.innerHTML = '';

      products.forEach(product => {{
        const card = document.createElement('article');
        card.className = 'card';
        card.innerHTML = `
          <div class="product-art" style="background: ${{product.gradient}};">
            <div class="tag">${{product.tag}}</div>
          </div>
          <div class="card-body">
            <div class="title-row">
              <h3>${{product.name}}</h3>
              <div class="price">${{money(product.price)}}</div>
            </div>
            <div class="muted">${{product.description}}</div>
            <div class="sizes">${{product.sizes.map(size => `<span class="size-chip">${{size}}</span>`).join('')}}</div>
            <div class="card-actions">
              <select class="size-select" aria-label="Choose a size for ${{product.name}}">
                ${{product.sizes.map(size => `<option value="${{size}}">Size ${{size}}</option>`).join('')}}
              </select>
              <button class="add-button">Add to cart</button>
            </div>
          </div>
        `;

        const select = card.querySelector('select');
        const button = card.querySelector('button');
        button.addEventListener('click', () => addToCart(product.id, select.value));
        catalog.appendChild(card);
      }});
    }}

    function addToCart(productId, size) {{
      const existing = cart.find(item => item.product_id === productId && item.size === size);
      if (existing) {{
        existing.quantity += 1;
      }} else {{
        cart.push({{ product_id: productId, size, quantity: 1 }});
      }}
      saveCart();
      renderCart();
      showNotice('Added to cart.', 'success');
    }}

    function removeFromCart(index) {{
      cart.splice(index, 1);
      saveCart();
      renderCart();
    }}

    function updateQuantity(index, nextQuantity) {{
      const quantity = Math.max(1, Number(nextQuantity || 1));
      cart[index].quantity = quantity;
      saveCart();
      renderCart();
    }}

    function getProduct(productId) {{
      return products.find(p => p.id === productId);
    }}

    function computeSubtotal() {{
      return cart.reduce((sum, item) => {{
        const product = getProduct(item.product_id);
        return sum + (product ? Number(product.price) * Number(item.quantity) : 0);
      }}, 0);
    }}

    function renderCart() {{
      const cartItems = document.getElementById('cartItems');
      const count = cart.reduce((sum, item) => sum + Number(item.quantity), 0);
      document.getElementById('cartCount').textContent = String(count);

      if (!cart.length) {{
        cartItems.innerHTML = '<div class="cart-item"><strong>Your cart is empty.</strong><div class="tiny">Add a few shirts to place your first order.</div></div>';
      }} else {{
        cartItems.innerHTML = '';
        cart.forEach((item, index) => {{
          const product = getProduct(item.product_id);
          if (!product) return;
          const row = document.createElement('div');
          row.className = 'cart-item';
          row.innerHTML = `
            <div class="cart-line"><strong>${{product.name}}</strong><strong>${{money(Number(product.price) * Number(item.quantity))}}</strong></div>
            <div class="tiny">Size: ${{item.size}}</div>
            <div class="cart-line">
              <label class="tiny">Qty <input data-index="${{index}}" type="number" min="1" value="${{item.quantity}}" style="width:64px; margin-left:6px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04); color:white; padding:6px 8px;"></label>
              <button class="danger-link" data-remove="${{index}}">Remove</button>
            </div>
          `;
          cartItems.appendChild(row);
        }});

        cartItems.querySelectorAll('input[data-index]').forEach(input => {{
          input.addEventListener('change', (event) => updateQuantity(Number(event.target.dataset.index), event.target.value));
        }});

        cartItems.querySelectorAll('button[data-remove]').forEach(button => {{
          button.addEventListener('click', (event) => removeFromCart(Number(event.target.dataset.remove)));
        }});
      }}

      const subtotal = computeSubtotal();
      const shipping = cart.length ? flatShipping : 0;
      const total = subtotal + shipping;
      document.getElementById('subtotal').textContent = money(subtotal);
      document.getElementById('shipping').textContent = money(shipping);
      document.getElementById('total').textContent = money(total);
    }}

    function showNotice(message, kind) {{
      const notice = document.getElementById('notice');
      notice.className = `notice ${{kind}}`;
      notice.textContent = message;
    }}

    async function submitOrder(event) {{
      event.preventDefault();

      if (!cart.length) {{
        showNotice('Your cart is empty. Add a product before checking out.', 'error');
        return;
      }}

      const form = event.currentTarget;
      const payload = {{
        customer: {{
          name: form.name.value.trim(),
          email: form.email.value.trim(),
          address: form.address.value.trim(),
        }},
        items: cart,
      }};

      try {{
        const response = await fetch('/api/order', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload),
        }});

        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.error || 'Order failed.');
        }}

        cart = [];
        saveCart();
        renderCart();
        form.reset();
        showNotice(`Order placed successfully.\nOrder ID: ${{data.order_id}}\nTotal: ${{money(data.total)}}`, 'success');
      }} catch (error) {{
        showNotice(error.message || 'Something went wrong while placing the order.', 'error');
      }}
    }}

    init();
  </script>
</body>
</html>
"""


def decimal_money(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        amount = value
    else:
        amount = Decimal(str(value))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


PRODUCT_LOOKUP = {product["id"]: product for product in PRODUCTS}


class StoreHandler(BaseHTTPRequestHandler):
    server_version = "TShirtStore/1.0"

    def _send_json(self, payload: dict[str, Any] | list[Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("Request body is required.")
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Body must be valid JSON.") from exc

    def log_message(self, format: str, *args: Any) -> None:
        # Keeps terminal output readable but still logs activity.
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path in {"/", "/index.html"}:
            self._send_html(INDEX_HTML)
            return

        if path == "/api/products":
            self._send_json(PRODUCTS)
            return

        if path == "/health":
            self._send_json({"ok": True, "store": STORE_NAME})
            return

        self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/api/order":
            self._handle_order()
            return

        self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def _handle_order(self) -> None:
        try:
            payload = self._read_json_body()
            order = validate_and_build_order(payload)
            save_order(order)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except OSError:
            self._send_json({"error": "Could not save order on the server."}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(
            {
                "ok": True,
                "order_id": order["order_id"],
                "total": float(order["totals"]["total"]),
            },
            status=HTTPStatus.CREATED,
        )


def validate_and_build_order(payload: dict[str, Any]) -> dict[str, Any]:
    customer = payload.get("customer")
    items = payload.get("items")

    if not isinstance(customer, dict):
        raise ValueError("Customer details are required.")
    if not isinstance(items, list) or not items:
        raise ValueError("At least one cart item is required.")

    name = str(customer.get("name", "")).strip()
    email = str(customer.get("email", "")).strip()
    address = str(customer.get("address", "")).strip()

    if len(name) < 2:
        raise ValueError("Customer name is too short.")
    if "@" not in email or len(email) < 5:
        raise ValueError("A valid email is required.")
    if len(address) < 8:
        raise ValueError("Shipping address is too short.")

    normalized_items: list[dict[str, Any]] = []
    subtotal = Decimal("0.00")

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each cart item must be an object.")

        product_id = str(item.get("product_id", "")).strip()
        size = str(item.get("size", "")).strip()
        try:
            quantity = int(item.get("quantity", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("Quantity must be a whole number.") from exc

        product = PRODUCT_LOOKUP.get(product_id)
        if not product:
            raise ValueError(f"Unknown product: {product_id}")
        if size not in product["sizes"]:
            raise ValueError(f"Invalid size '{size}' for product '{product['name']}'.")
        if quantity < 1 or quantity > 25:
            raise ValueError("Quantity must be between 1 and 25.")

        unit_price = decimal_money(product["price"])
        line_total = decimal_money(unit_price * quantity)
        subtotal += line_total

        normalized_items.append(
            {
                "product_id": product["id"],
                "name": product["name"],
                "size": size,
                "quantity": quantity,
                "unit_price": str(unit_price),
                "line_total": str(line_total),
            }
        )

    shipping = decimal_money("6.00") if normalized_items else Decimal("0.00")
    total = decimal_money(subtotal + shipping)

    return {
        "order_id": uuid.uuid4().hex[:10].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "customer": {
            "name": name,
            "email": email,
            "address": address,
        },
        "items": normalized_items,
        "totals": {
            "subtotal": str(decimal_money(subtotal)),
            "shipping": str(shipping),
            "total": str(total),
        },
        "currency_symbol": CURRENCY_SYMBOL,
    }


def save_order(order: dict[str, Any]) -> None:
    existing: list[dict[str, Any]] = []
    if ORDERS_FILE.exists():
        try:
            existing = json.loads(ORDERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    existing.append(order)
    ORDERS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def run() -> None:
    host = os.getenv("HOST", HOST)
    try:
        port = int(os.getenv("PORT", str(PORT)))
    except ValueError:
        port = PORT

    server = ThreadingHTTPServer((host, port), StoreHandler)
    print(f"{STORE_NAME} running at http://{host}:{port}")
    print(f"Orders will be saved to: {ORDERS_FILE}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
