import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Search, ShoppingCart, CreditCard, CheckCircle2, Clock, Filter, Package } from "lucide-react";

export const Route = createFileRoute("/orders")({
  component: OnlineOrdersPage,
});

const MOCK_ORDERS = [
  { id: "ORD-9482", customer: "Rajesh Kumar", type: "Delivery", items: 4, total: 1250, status: "Pending", payment: "UPI", time: "10 min ago" },
  { id: "ORD-9481", customer: "Priya Singh", type: "Pickup", items: 2, total: 340, status: "Ready", payment: "Card", time: "35 min ago" },
  { id: "ORD-9480", customer: "Anand M", type: "Delivery", items: 12, total: 4200, status: "Delivered", payment: "Cash on Delivery", time: "2 hours ago" },
  { id: "ORD-9479", customer: "Kavitha", type: "Delivery", items: 5, total: 850, status: "Delivered", payment: "UPI", time: "4 hours ago" },
];

function OnlineOrdersPage() {
  const [tab, setTab] = useState("All");

  const filteredOrders = MOCK_ORDERS.filter(o => tab === "All" ? true : tab === "Pending" ? o.status === "Pending" || o.status === "Ready" : o.status === "Delivered");

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Online Orders & Payments</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage delivery, store pickups, and payment gateway transactions.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-card rounded-xl shadow-card p-5 border-l-4 border-primary">
          <div className="flex justify-between items-start mb-2">
            <div className="text-sm font-semibold">Today's Revenue</div>
            <CreditCard className="w-5 h-5 text-primary opacity-80" />
          </div>
          <div className="text-3xl font-black">₹6,640</div>
          <div className="text-xs text-muted-foreground mt-1 text-success flex items-center gap-1">
            +14% from yesterday
          </div>
        </div>
        <div className="bg-card rounded-xl shadow-card p-5 border-l-4 border-warning">
          <div className="flex justify-between items-start mb-2">
            <div className="text-sm font-semibold">Pending Actions</div>
            <Clock className="w-5 h-5 text-warning opacity-80" />
          </div>
          <div className="text-3xl font-black">2</div>
          <div className="text-xs text-muted-foreground mt-1">
            1 Delivery, 1 Pickup
          </div>
        </div>
        <div className="bg-card rounded-xl shadow-card p-5 border-l-4 border-success flex flex-col justify-center items-center text-center bg-gradient-to-br from-success/5 to-success/10 cursor-pointer hover:shadow-md transition-shadow">
          <ShoppingCart className="w-6 h-6 text-success mb-2" />
          <div className="font-bold text-foreground">Payment Gateway Active</div>
          <div className="text-xs text-muted-foreground mt-1">UPI & Cards receiving</div>
        </div>
      </div>

      <div className="bg-card rounded-xl shadow-card overflow-hidden">
        <div className="flex border-b border-border bg-background/50 px-2 pt-2">
          {["All", "Pending", "Completed"].map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}>
              {t}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2 pr-4 pb-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input placeholder="Search Order ID..." className="pl-9 pr-3 py-1.5 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary" />
            </div>
          </div>
        </div>

        <div className="divide-y divide-border">
          {filteredOrders.map(o => (
            <div key={o.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-muted/30">
              <div className="flex items-start gap-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                  o.type === 'Pickup' ? 'bg-accent text-primary' : 'bg-success/10 text-success'
                }`}>
                  <Package className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-foreground">{o.id}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                      o.status === 'Pending' ? 'bg-warning/20 text-warning' : 
                      o.status === 'Ready' ? 'bg-primary/20 text-primary' : 
                      'bg-success/20 text-success'
                    }`}>{o.status}</span>
                  </div>
                  <div className="text-sm font-medium text-foreground mt-0.5">{o.customer}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                    <span>{o.items} items</span>
                    <span>•</span>
                    <span>{o.type}</span>
                    <span>•</span>
                    <span>{o.time}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 md:ml-auto">
                <div className="text-right">
                  <div className="font-bold text-foreground">₹{o.total.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1 justify-end">
                    {o.payment === 'UPI' || o.payment === 'Card' ? <CheckCircle2 className="w-3 h-3 text-success" /> : null}
                    {o.payment}
                  </div>
                </div>
                {o.status === 'Pending' && (
                  <button className="bg-primary text-white text-xs font-semibold px-4 py-2 rounded-lg hover:opacity-90">
                    Accept
                  </button>
                )}
                {o.status === 'Ready' && (
                  <button className="bg-success text-white text-xs font-semibold px-4 py-2 rounded-lg hover:opacity-90">
                    Handover
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
