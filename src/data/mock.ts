export type Status = "Healthy" | "Low Stock" | "Critical" | "Dead Stock";

export interface Product {
  id: string;
  name: string;
  category: string;
  unit: string;
  mrp: number;
  stock: number;
  status: Status;
  aiPick?: boolean;
  /** days without movement — used for urgency scoring */
  daysIdle?: number;
  /** keyword(s) for placeholder image lookup */
  img: string;
  /** days until expiry */
  expiryDays?: number;
  /** estimated weight per unit in kg (for carbon calc) */
  weightKg?: number;
}

export const imgFor = (p: Pick<Product, "img">) =>
  `https://source.unsplash.com/160x160/?${encodeURIComponent(p.img)}`;

export const categories = [
  "Rice & Grains", "Cooking Oil", "Dal & Pulses", "Spices & Masala",
  "Flour & Rava", "Sugar & Salt", "Biscuits & Snacks", "Beverages",
  "Soaps & Detergents", "Dairy & Eggs",
];

export const products: Product[] = [
  { id: "p1",  name: "Sona Masoori Rice",   category: "Rice & Grains",        unit: "Kg",     mrp: 58,  stock: 250, status: "Healthy",    img: "rice,bag",           weightKg: 1 },
  { id: "p2",  name: "Ponni Rice",           category: "Rice & Grains",        unit: "Kg",     mrp: 62,  stock: 180, status: "Healthy",    img: "rice,grain",         weightKg: 1 },
  { id: "p3",  name: "Sunflower Oil",        category: "Cooking Oil",          unit: "Litre",  mrp: 148, stock: 12,  status: "Low Stock",  aiPick: true, img: "sunflower,oil,bottle", daysIdle: 3, expiryDays: 28, weightKg: 1 },
  { id: "p4",  name: "Groundnut Oil",        category: "Cooking Oil",          unit: "Litre",  mrp: 210, stock: 8,   status: "Critical",   aiPick: true, img: "peanut,oil",           daysIdle: 7, expiryDays: 6,  weightKg: 1 },
  { id: "p5",  name: "Toor Dal",             category: "Dal & Pulses",         unit: "Kg",     mrp: 140, stock: 75,  status: "Healthy",    img: "lentils,dal",        weightKg: 1 },
  { id: "p6",  name: "Urad Dal",             category: "Dal & Pulses",         unit: "Kg",     mrp: 125, stock: 6,   status: "Critical",   aiPick: true, img: "urad,lentils",         daysIdle: 5, expiryDays: 4,  weightKg: 1 },
  { id: "p7",  name: "Turmeric Powder",      category: "Spices & Masala",      unit: "Packet", mrp: 65,  stock: 120, status: "Healthy",    img: "turmeric,powder",    weightKg: 0.1 },
  { id: "p8",  name: "Red Chilli Powder",    category: "Spices & Masala",      unit: "Packet", mrp: 75,  stock: 4,   status: "Critical",   aiPick: true, img: "chilli,powder",        daysIdle: 9, expiryDays: 5,  weightKg: 0.1 },
  { id: "p9",  name: "Wheat Flour (Atta)",   category: "Flour & Rava",         unit: "Kg",     mrp: 45,  stock: 150, status: "Healthy",    img: "flour,wheat",        weightKg: 1 },
  { id: "p10", name: "Sugar",                category: "Sugar & Salt",         unit: "Kg",     mrp: 44,  stock: 200, status: "Healthy",    img: "sugar,white",        weightKg: 1 },
  { id: "p11", name: "Parle-G Biscuit",      category: "Biscuits & Snacks",    unit: "Pcs",    mrp: 10,  stock: 300, status: "Healthy",    img: "biscuit,cookie",     weightKg: 0.08, expiryDays: 22 },
  { id: "p12", name: "Tata Tea Premium",     category: "Beverages",            unit: "Packet", mrp: 145, stock: 9,   status: "Low Stock",  aiPick: true, img: "tea,packet",           daysIdle: 4, expiryDays: 180, weightKg: 0.25 },
  { id: "p13", name: "Surf Excel",           category: "Soaps & Detergents",   unit: "Packet", mrp: 95,  stock: 50,  status: "Healthy",    img: "detergent,powder",   weightKg: 0.5 },
  { id: "p14", name: "Aavin Milk Packet",    category: "Dairy & Eggs",         unit: "Litre",  mrp: 27,  stock: 120, status: "Healthy",    img: "milk,packet",        weightKg: 1,   expiryDays: 2 },
  { id: "p15", name: "Garam Masala",         category: "Spices & Masala",      unit: "Packet", mrp: 85,  stock: 3,   status: "Dead Stock", aiPick: true, img: "garam,masala,spice",   daysIdle: 14, expiryDays: 8, weightKg: 0.1 },
  { id: "p16", name: "Coconut Oil",          category: "Cooking Oil",          unit: "Litre",  mrp: 225, stock: 30,  status: "Healthy",    img: "coconut,oil",        weightKg: 1 },
  { id: "p17", name: "Bru Coffee",           category: "Beverages",            unit: "Packet", mrp: 130, stock: 60,  status: "Healthy",    img: "coffee,jar",         weightKg: 0.2 },
  { id: "p18", name: "Eggs (Tray)",          category: "Dairy & Eggs",         unit: "Pcs",    mrp: 7,   stock: 500, status: "Healthy",    img: "eggs,tray",          weightKg: 0.06, expiryDays: 10 },
];

export interface Customer {
  id: string;
  name: string;
  phone: string;
  type: "Credit" | "Regular" | "Business" | "Frequent";
  outstanding: number;
  lastPurchase: string;
}

export const customers: Customer[] = [
  { id: "c1",  name: "Murugan S",      phone: "98765 43201", type: "Credit",  outstanding: 1200, lastPurchase: "2 days ago" },
  { id: "c2",  name: "Lakshmi Devi",   phone: "98765 43202", type: "Frequent", outstanding: 0,    lastPurchase: "Today" },
  { id: "c3",  name: "Rajan K",        phone: "98765 43203", type: "Credit",  outstanding: 3400, lastPurchase: "5 days ago" },
  { id: "c4",  name: "Krishnamurthy",  phone: "98765 43205", type: "Business",outstanding: 6800, lastPurchase: "1 week ago" },
  { id: "c5",  name: "Annamalai T",    phone: "98765 43206", type: "Regular", outstanding: 0,    lastPurchase: "Yesterday" },
  { id: "c6",  name: "Valli Ammal",    phone: "98765 43207", type: "Frequent",outstanding: 0,    lastPurchase: "3 days ago" },
  { id: "c7",  name: "Senthil Kumar",  phone: "98765 43208", type: "Business",outstanding: 2200, lastPurchase: "4 days ago" },
  { id: "c8",  name: "Meenakshi P",    phone: "98765 43209", type: "Frequent", outstanding: 0,    lastPurchase: "Today" },
  { id: "c9",  name: "Palani G",       phone: "98765 43210", type: "Credit",  outstanding: 4100, lastPurchase: "6 days ago" },
  { id: "c10", name: "Sundaram B",     phone: "98765 43212", type: "Regular", outstanding: 0,    lastPurchase: "Yesterday" },
];

export interface Offer {
  productIds: string[];
  discountType: "percent" | "flat";
  discountValue: number;
  validFrom: string;
  validTo: string;
}

// simple in-memory shared offer store
let currentOffer: Offer | null = {
  productIds: ["p3"],
  discountType: "percent",
  discountValue: 10,
  validFrom: "26 May 2026",
  validTo: "01 Jun 2026",
};
const listeners = new Set<() => void>();
export const offerStore = {
  get: () => currentOffer,
  set: (o: Offer | null) => { currentOffer = o; listeners.forEach((l) => l()); },
  subscribe: (l: () => void) => { listeners.add(l); return () => { listeners.delete(l); }; },
};

// ─── NGO data ───────────────────────────────────────────────────────────────
export type NgoCategory = "Food Donation" | "Children" | "Elder Care" | "Community Support";

export interface NGO {
  id: string;
  name: string;
  contact: string;
  address: string;
  category: NgoCategory;
  emoji: string;
  totalReceived: number; // kg of food received
}

export const ngos: NGO[] = [
  { id: "n1", name: "Perambalur Food Bank",     contact: "98401 11001", address: "Gandhi Nagar, Perambalur",     category: "Food Donation",      emoji: "🍱", totalReceived: 482 },
  { id: "n2", name: "Annai Children's Trust",   contact: "98401 11002", address: "Bus Stand Road, Perambalur",   category: "Children",           emoji: "👶", totalReceived: 214 },
  { id: "n3", name: "Vayothikam Elder Home",    contact: "98401 11003", address: "Ariyalur Bypass, Perambalur",  category: "Elder Care",         emoji: "👴", totalReceived: 318 },
  { id: "n4", name: "Aadhirai Community Trust", contact: "98401 11004", address: "Main Market, Perambalur",      category: "Community Support",  emoji: "🤝", totalReceived: 540 },
  { id: "n5", name: "Green Meals Society",      contact: "98401 11005", address: "College Road, Perambalur",     category: "Food Donation",      emoji: "🌱", totalReceived: 267 },
];

// ─── Donation records ────────────────────────────────────────────────────────
export interface DonationRecord {
  id: string;
  productId: string;
  productName: string;
  ngoId: string;
  ngoName: string;
  quantity: number;
  weightKg: number;
  carbonSavedKg: number;
  date: string;
}

// Carbon saved ≈ 2.5 kg CO₂ per kg food waste avoided
const CO2_PER_KG = 2.5;

let donationRecords: DonationRecord[] = [
  { id: "d1", productId: "p14", productName: "Aavin Milk Packet",  ngoId: "n1", ngoName: "Perambalur Food Bank",     quantity: 30, weightKg: 30,   carbonSavedKg: 75,   date: "28 May 2026" },
  { id: "d2", productId: "p11", productName: "Parle-G Biscuit",    ngoId: "n2", ngoName: "Annai Children's Trust",   quantity: 50, weightKg: 4,    carbonSavedKg: 10,   date: "22 May 2026" },
  { id: "d3", productId: "p18", productName: "Eggs (Tray)",        ngoId: "n3", ngoName: "Vayothikam Elder Home",    quantity: 60, weightKg: 3.6,  carbonSavedKg: 9,    date: "15 May 2026" },
  { id: "d4", productId: "p3",  productName: "Sunflower Oil",      ngoId: "n4", ngoName: "Aadhirai Community Trust", quantity: 5,  weightKg: 5,    carbonSavedKg: 12.5, date: "10 May 2026" },
];

const donationListeners = new Set<() => void>();

export const donationStore = {
  getAll: () => donationRecords,
  add: (record: Omit<DonationRecord, "id" | "carbonSavedKg">) => {
    const newRec: DonationRecord = {
      ...record,
      id: `d${Date.now()}`,
      carbonSavedKg: record.weightKg * CO2_PER_KG,
    };
    donationRecords = [newRec, ...donationRecords];
    donationListeners.forEach((l) => l());
    return newRec;
  },
  subscribe: (l: () => void) => { donationListeners.add(l); return () => { donationListeners.delete(l); }; },
};

// ─── Carbon metrics helpers ──────────────────────────────────────────────────
export function getCarbonMetrics() {
  const records = donationStore.getAll();
  const totalFoodKg   = records.reduce((s, r) => s + r.weightKg, 0);
  const totalCarbon   = records.reduce((s, r) => s + r.carbonSavedKg, 0);
  const totalProducts = records.reduce((s, r) => s + r.quantity, 0);
  // 0.5 kg food per meal, ~4 meals/day per family
  const familiesHelped = Math.round(totalFoodKg / (0.5 * 4));
  return { totalFoodKg, totalCarbon, totalProducts, familiesHelped };
}

// Monthly trends (last 6 months, mock)
export const monthlyDonationTrend = [
  { month: "Jan", foodKg: 12, carbon: 30,  products: 18 },
  { month: "Feb", foodKg: 18, carbon: 45,  products: 24 },
  { month: "Mar", foodKg: 22, carbon: 55,  products: 30 },
  { month: "Apr", foodKg: 28, carbon: 70,  products: 38 },
  { month: "May", foodKg: 42, carbon: 105, products: 145 },
  { month: "Jun", foodKg: 8,  carbon: 20,  products: 5  },
];
