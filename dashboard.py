from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent
ORDERS_CSV = DATA_DIR / "orders_rows.csv"
ITEMS_CSV = DATA_DIR / "order_items_rows.csv"
LOCAL_TIMEZONE = "Asia/Jakarta"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(ORDERS_CSV)
    items = pd.read_csv(ITEMS_CSV)

    # Parse timestamps and convert to local operational timezone.
    datetime_columns = ["created_at", "updated_at", "started_at", "completed_at", "paid_at"]
    for col in datetime_columns:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors="coerce", utc=True).dt.tz_convert(LOCAL_TIMEZONE)

    if "created_at" in items.columns:
        items["created_at"] = pd.to_datetime(items["created_at"], errors="coerce", utc=True).dt.tz_convert(LOCAL_TIMEZONE)

    numeric_order_cols = ["subtotal", "tax", "total", "payment_amount", "change_amount"]
    for col in numeric_order_cols:
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce").fillna(0)

    numeric_item_cols = ["price", "quantity", "subtotal"]
    for col in numeric_item_cols:
        if col in items.columns:
            items[col] = pd.to_numeric(items[col], errors="coerce").fillna(0)

    if "is_paid" in orders.columns:
        orders["is_paid"] = orders["is_paid"].astype(str).str.lower().eq("true")

    orders["customer_name"] = orders.get("customer_name", "Guest").fillna("Guest")
    orders["payment_method"] = orders.get("payment_method", "unknown").fillna("unknown")
    orders["status"] = orders.get("status", "unknown").fillna("unknown")
    orders["order_type"] = orders.get("order_type", "unknown").fillna("unknown")

    # Enriched date dimensions for filtering and trend analysis.
    orders["date"] = orders["created_at"].dt.date
    orders["hour"] = orders["created_at"].dt.hour
    orders["weekday"] = orders["created_at"].dt.day_name()

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    orders["weekday"] = pd.Categorical(orders["weekday"], categories=weekday_order, ordered=True)

    return orders, items


def money(value: float) -> str:
    return f"Rp {value:,.0f}".replace(",", ".")


def apply_theme(dark_mode: bool) -> None:
    if dark_mode:
        app_gradient = "radial-gradient(circle at top left, #111827 0%, #0b1220 55%, #020617 100%)"
        text_color = "#e5e7eb"
        muted_text = "#9ca3af"
        card_bg = "rgba(15, 23, 42, 0.72)"
        border_color = "rgba(148, 163, 184, 0.28)"
    else:
        app_gradient = "radial-gradient(circle at top left, #f4fbf8 0%, #eef6ff 55%, #ffffff 100%)"
        text_color = "#0f172a"
        muted_text = "#475569"
        card_bg = "rgba(255, 255, 255, 0.72)"
        border_color = "rgba(100, 116, 139, 0.22)"

    st.markdown(
        f"""
        <style>
            .stApp {{
                background: {app_gradient};
                color: {text_color};
            }}

            [data-testid="stSidebar"] {{
                border-right: 1px solid {border_color};
            }}

            [data-testid="stMetric"] {{
                background: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 8px 10px;
                backdrop-filter: blur(4px);
            }}

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"],
            [data-testid="stMarkdownContainer"],
            .stSubheader,
            .stCaption {{
                color: {text_color};
            }}

            .stCaption {{
                color: {muted_text};
            }}

            [data-testid="stDataFrame"] {{
                border: 1px solid {border_color};
                border-radius: 10px;
                overflow: hidden;
            }}

            [data-testid="stMetricValue"] {{
                font-size: 1.5rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_filters(orders: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")

    min_date = orders["date"].min()
    max_date = orders["date"].max()

    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    payment_options = sorted(orders["payment_method"].dropna().unique().tolist())
    selected_payment = st.sidebar.multiselect(
        "Payment method",
        options=payment_options,
        default=payment_options,
    )

    status_options = sorted(orders["status"].dropna().unique().tolist())
    selected_status = st.sidebar.multiselect(
        "Order status",
        options=status_options,
        default=status_options,
    )

    order_type_options = sorted(orders["order_type"].dropna().unique().tolist())
    selected_order_type = st.sidebar.multiselect(
        "Order type",
        options=order_type_options,
        default=order_type_options,
    )

    paid_only = st.sidebar.toggle("Paid only", value=True)

    filtered = orders.loc[
        (orders["date"] >= start_date)
        & (orders["date"] <= end_date)
        & (orders["payment_method"].isin(selected_payment))
        & (orders["status"].isin(selected_status))
        & (orders["order_type"].isin(selected_order_type))
    ].copy()

    if paid_only:
        filtered = filtered.loc[filtered["is_paid"]]

    st.sidebar.caption(f"Filtered orders: {len(filtered):,}")
    return filtered


def build_order_items(filtered_orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    order_ids = filtered_orders["id"].dropna().unique().tolist()
    if not order_ids:
        return pd.DataFrame(columns=items.columns)

    item_subset = items.loc[items["order_id"].isin(order_ids)].copy()
    item_subset["line_revenue"] = item_subset["subtotal"].where(item_subset["subtotal"] > 0, item_subset["price"] * item_subset["quantity"])
    return item_subset


def compute_peak_hours(filtered_orders: pd.DataFrame) -> pd.DataFrame:
    peak = (
        filtered_orders.groupby("hour", dropna=False)
        .agg(
            transactions=("id", "count"),
            revenue=("total", "sum"),
            avg_ticket=("total", "mean"),
        )
        .reset_index()
        .sort_values("hour")
    )
    peak["hour_label"] = peak["hour"].fillna(-1).astype(int).astype(str).str.zfill(2) + ":00"
    return peak


def render_dashboard(filtered_orders: pd.DataFrame, filtered_items: pd.DataFrame, dark_mode: bool) -> None:
    chart_template = "plotly_dark" if dark_mode else "plotly_white"
    chart_text_color = "#e5e7eb" if dark_mode else "#0f172a"

    total_revenue = float(filtered_orders["total"].sum())
    total_orders = int(filtered_orders["id"].count())
    total_items = float(filtered_items["quantity"].sum())
    avg_ticket = total_revenue / total_orders if total_orders > 0 else 0
    unique_customers = int(filtered_orders["customer_name"].replace("", "Guest").nunique())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", money(total_revenue))
    c2.metric("Transactions", f"{total_orders:,}")
    c3.metric("Items Sold", f"{int(total_items):,}")
    c4.metric("Avg Ticket", money(avg_ticket))
    c5.metric("Unique Customers", f"{unique_customers:,}")

    daily = (
        filtered_orders.groupby("date", dropna=False)
        .agg(revenue=("total", "sum"), transactions=("id", "count"))
        .reset_index()
        .sort_values("date")
    )

    payment = (
        filtered_orders.groupby("payment_method", dropna=False)
        .agg(transactions=("id", "count"), revenue=("total", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    top_menu = (
        filtered_items.groupby("product_name", dropna=False)
        .agg(quantity=("quantity", "sum"), revenue=("line_revenue", "sum"))
        .reset_index()
        .sort_values(["quantity", "revenue"], ascending=[False, False])
    )

    peak_hours = compute_peak_hours(filtered_orders)

    weekday_hour = (
        filtered_orders.groupby(["weekday", "hour"], observed=True)
        .agg(transactions=("id", "count"))
        .reset_index()
    )

    st.subheader("Sales Trend")
    trend_fig = px.line(
        daily,
        x="date",
        y="revenue",
        markers=True,
        title="Daily Revenue",
        template=chart_template,
    )
    trend_fig.update_layout(
        yaxis_title="Revenue",
        xaxis_title="Date",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=chart_text_color,
    )
    st.plotly_chart(trend_fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Jam Rame")
        peak_fig = px.bar(
            peak_hours,
            x="hour_label",
            y="transactions",
            color="revenue",
            color_continuous_scale="Tealgrn",
            title="Hourly Transactions and Revenue Intensity",
            template=chart_template,
        )
        peak_fig.update_layout(
            xaxis_title="Hour",
            yaxis_title="Transactions",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=chart_text_color,
        )
        st.plotly_chart(peak_fig, use_container_width=True)

    with right:
        st.subheader("Payment Mix")
        payment_fig = px.pie(
            payment,
            names="payment_method",
            values="revenue",
            hole=0.45,
            title="Revenue Share by Payment Method",
            template=chart_template,
        )
        payment_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=chart_text_color,
        )
        st.plotly_chart(payment_fig, use_container_width=True)

    st.subheader("Heatmap Hari x Jam")
    if not weekday_hour.empty:
        heatmap_fig = px.density_heatmap(
            weekday_hour,
            x="hour",
            y="weekday",
            z="transactions",
            histfunc="sum",
            color_continuous_scale="Sunset",
            title="Transaction Density by Weekday and Hour",
            template=chart_template,
        )
        heatmap_fig.update_layout(
            xaxis_title="Hour",
            yaxis_title="Weekday",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=chart_text_color,
        )
        st.plotly_chart(heatmap_fig, use_container_width=True)
    else:
        st.info("No data available for weekday-hour heatmap.")

    st.subheader("Top Selling Menu")
    st.dataframe(
        top_menu.head(25).assign(
            quantity=lambda d: d["quantity"].astype(int),
            revenue=lambda d: d["revenue"].round(0).astype(int),
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Detailed Transactions")
    tx_cols = [
        "order_number",
        "created_at",
        "customer_name",
        "order_type",
        "payment_method",
        "status",
        "is_paid",
        "total",
    ]
    tx_cols = [c for c in tx_cols if c in filtered_orders.columns]
    st.dataframe(
        filtered_orders[tx_cols].sort_values("created_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="Download filtered transactions CSV",
        data=filtered_orders.to_csv(index=False).encode("utf-8"),
        file_name="filtered_transactions.csv",
        mime="text/csv",
    )

    st.download_button(
        label="Download top menu CSV",
        data=top_menu.to_csv(index=False).encode("utf-8"),
        file_name="top_selling_menu.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Exa Warkop Detailed Analytics",
        page_icon="chart_with_upwards_trend",
        layout="wide",
    )

    st.sidebar.header("Display")
    dark_mode = st.sidebar.toggle("Dark mode", value=False)
    apply_theme(dark_mode)

    st.title("Exa Warkop Analytics Dashboard")
    st.caption("Detailed sales intelligence from backup CSV data")

    if not ORDERS_CSV.exists() or not ITEMS_CSV.exists():
        st.error("CSV files not found. Place orders_rows.csv and order_items_rows.csv in this folder.")
        return

    try:
        orders, items = load_data()
    except Exception as exc:
        st.exception(exc)
        return

    filtered_orders = apply_filters(orders)

    if filtered_orders.empty:
        st.warning("No data for selected filters. Adjust date or filter values.")
        return

    filtered_items = build_order_items(filtered_orders, items)
    render_dashboard(filtered_orders, filtered_items, dark_mode)


if __name__ == "__main__":
    main()
