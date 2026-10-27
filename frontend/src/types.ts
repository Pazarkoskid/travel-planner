export type Role = "TOURIST" | "BUSINESS" | "ADMIN";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  bio: string;
  is_profile_public: boolean;
}

export interface City {
  id: number;
  name: string;
  slug: string;
  region: string;
  description: string;
  center_lat: number;
  center_lng: number;
  place_count: number;
  required_landmarks: number;
  image_url: string;
  image_credit: string;
}

export interface Place {
  id: number;
  city: number;
  city_name: string;
  name: string;
  slug: string;
  category: string;
  category_label: string;
  description: string;
  lat: number;
  lng: number;
  visit_duration_min: number;
  price_eur: string | null;
  opening_time: string | null;
  closing_time: string | null;
  source: string;
  verified_at: string | null;
  is_required_landmark: boolean;
  checkin_radius_m: number;
  badge_holders: number | null;
  image_url: string;
  image_credit: string;
  wheelchair: Wheelchair;
  wheelchair_label: string;
  accessibility_notes: string;
}

export type Wheelchair = "YES" | "LIMITED" | "NO" | "UNKNOWN";

export interface ItineraryItem {
  id: number;
  source_type: "PLACE" | "BUSINESS" | "MEAL" | "BREAK";
  place: number | null;
  business: number | null;
  title: string;
  start_time: string;
  end_time: string;
  travel_minutes_from_prev: number;
  distance_km_from_prev: number;
  est_cost: string | null;
  reason: string;
  warning: string;
  lat: number | null;
  lng: number | null;
  category: string | null;
  image_url: string;
  wheelchair: Wheelchair | null;
  accessibility_notes: string;
}

export interface PlanRun {
  id: number;
  provider: string;
  model: string;
  routing_provider: string;
  rejected_ids: string[];
  validation_result: { valid: boolean; errors: string[] };
  metrics: Record<string, number | null>;
  duration_ms: number;
  created_at: string;
}

export interface Trip {
  id: number;
  city: number;
  city_name: string;
  title: string;
  start_date: string;
  days: number;
  guests: number;
  budget: string | null;
  interests: string[];
  pace: string;
  transport: string;
  mobility: "standard" | "reduced" | "wheelchair";
  warnings: string[];
  status: string;
  modifiers: { active?: string[]; last_instruction?: string };
  itinerary_days?: { day_number: number; date: string; notes: string; items: ItineraryItem[] }[];
  latest_run?: PlanRun | null;
}

export interface Business {
  id: number;
  name: string;
  type: string;
  type_label: string;
  description: string;
  city: number;
  city_name: string;
  city_image_url: string;
  image_url: string;
  logo: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  lat: number;
  lng: number;
  is_sponsored: boolean;
  avg_rating: number | null;
  review_count: number;
}

export interface AccommodationResult {
  id: number;
  business: Business;
  title: string;
  type_label: string;
  description: string;
  max_guests: number;
  bedrooms: number;
  beds: number;
  amenities: string[];
  rules: string;
  cleaning_fee: string;
  free_cancellation_days: number;
  image_url: string;
  avg_rating: number | null;
  review_count: number;
  recommendation_reason: string;
  quote: null | { unit_id: number; unit_name: string; nights: number; subtotal: string; fees: string; total: string };
}

export interface Departure {
  id: number;
  starts_at: string;
  capacity: number;
  reserved_seats: number;
  remaining_seats: number;
  status: string;
}

export interface TourStop {
  name: string;
  minutes: number;
  stop_min?: number;
  lat?: number | null;
  lng?: number | null;
  note?: string;
}

export interface BoatTour {
  id: number;
  business: Business;
  title: string;
  route: string;
  description: string;
  stops: TourStop[];
  includes: string;
  duration_min: number;
  price_per_person: string;
  departure_point: string;
  rules: string;
  upcoming_departures: Departure[];
}

export interface Reservation {
  id: number;
  business: number;
  business_name: string;
  user_name: string;
  service_type: string;
  service_label: string;
  status: string;
  status_label: string;
  guests: number;
  unit_name: string | null;
  check_in: string | null;
  check_out: string | null;
  departure_at: string | null;
  reserved_for: string | null;
  pickup: string;
  destination: string;
  notes: string;
  business_message: string;
  proposed_datetime: string | null;
  quoted_price: string | null;
  total_price: string | null;
  requested_at: string;
  has_review: boolean;
  can_review: boolean;
  history: { from_status: string; to_status: string; note: string; created_at: string }[];
}

export interface Review {
  id: number;
  username: string;
  rating: number;
  dimension_scores: Record<string, number>;
  comment: string;
  is_verified_booking: boolean;
  created_at: string;
  reply: { reply_text: string } | null;
  service_type?: string;
  business_name?: string;
}

export interface Badge {
  id: number;
  code: string;
  name: string;
  description: string;
  kind: "PLACE" | "LEVEL" | "REGION" | "CATEGORY";
  level: string;
  icon: string;
  art?: string;
  available?: boolean;
  sort?: number;
  holders_count?: number;
}

export interface CityProgress {
  city: number;
  city_name: string;
  city_slug: string;
  documented_required: number;
  required_total: number;
  documented_any: number;
  percent: number;
}

export interface Photo {
  id: number;
  place: number;
  place_name: string;
  image: string;
  caption: string;
  is_public: boolean;
  photographer: string;
  taken_at: string | null;
  created_at: string;
  like_count: number;
  liked_by_me: boolean;
}

export type Relation = "none" | "friends" | "outgoing" | "incoming";

export interface Person {
  username: string;
  name: string;
  bio: string;
  badges: number | null;
  is_public: boolean;
  relation: Relation;
  request_id: number | null;
  since?: string;
}

export interface CheckIn {
  id: number;
  place: number;
  place_name: string;
  image: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  distance_m: number | null;
  verification_notes: string[];
  created_at: string;
  username?: string;
}

export interface TaxiService {
  id: number;
  business: Business;
  service_area: string;
  passenger_capacity: number;
  base_fare: string | null;
  per_km: string | null;
  available_24h: boolean;
  vehicles: string;
  languages: string;
  fare_info: string;
}

export interface TransitLine {
  code: string;
  name: string;
  route: string;
  first: string;
  last: string;
  every_min: number;
  duration_min: number;
  price: number;
}

export interface RentalItem {
  name: string;
  per_hour: number | null;
  per_day: number | null;
}

export interface TransportService {
  id: number;
  business: Business;
  service_area: string;
  opening_hours: string;
  lines: TransitLine[];
  rentals: RentalItem[];
  price_info: string;
  payment: string;
  languages: string;
  features: string[];
}

export interface MenuItem {
  name: string;
  price: number | null;
  note?: string;
}

export interface Restaurant {
  id: number;
  business: Business;
  opening_hours: Record<string, string[] | string | null>;
  menu: MenuItem[];
  price_range: string;
  cuisine: string;
  max_party_size: number;
}

export interface WeatherDay {
  date: string;
  min: number;
  max: number;
  icon: string;
  description: string;
  pop: number;
  wind: number;
}

export interface Weather {
  location: string;
  current: { temp: number; feels_like: number; humidity: number; wind: number; icon: string; description: string };
  daily: WeatherDay[];
  source: string;
  fetched_at: string;
}
