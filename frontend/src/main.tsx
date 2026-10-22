import { t } from "./i18n";
import React, { ReactNode } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import Home from "./pages/Home";
import { Login, Register } from "./pages/Auth";
import { TripDetail, TripList, TripNew } from "./pages/Trips";
import { PlaceDetail, PlaceList } from "./pages/Places";
import { Accommodations, BoatTours, OtherServices } from "./pages/Services";
import MyReservations from "./pages/Reservations";
import BusinessDashboard from "./pages/Business";
import { MyProfile, PublicProfilePage } from "./pages/Profile";
import AdminPanel from "./pages/Admin";
import Credits from "./pages/Credits";
import BadgesPage from "./pages/Badges";
import FriendsPage from "./pages/Friends";
import { AccommodationDetail, BoatTourDetail, RestaurantDetail, TaxiDetail } from "./pages/Listings";
import { BusinessEditPage, NewBusinessPage } from "./pages/BusinessEdit";
import "@fontsource/onest/400.css";
import "@fontsource/onest/500.css";
import "@fontsource/onest/600.css";
import "@fontsource/onest/700.css";
import "@fontsource/marck-script/cyrillic-400.css";
import "@fontsource/marck-script/latin-400.css";
import "./styles.css";
import { registerServiceWorker } from "./pwa";

registerServiceWorker();

function Protected({ children, roles }: { children: ReactNode; roles?: string[] }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname + loc.search }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
            <Route path="places" element={<PlaceList />} />
            <Route path="places/:id" element={<PlaceDetail />} />
            <Route path="stay" element={<Accommodations />} />
            <Route path="boat-tours" element={<BoatTours />} />
            <Route path="services" element={<OtherServices />} />
            <Route path="stay/:id" element={<AccommodationDetail />} />
            <Route path="boat-tours/:id" element={<BoatTourDetail />} />
            <Route path="taxi/:id" element={<TaxiDetail />} />
            <Route path="restaurants/:id" element={<RestaurantDetail />} />
            <Route path="u/:username" element={<PublicProfilePage />} />
            <Route path="credits" element={<Credits />} />
            <Route path="badges" element={<BadgesPage />} />
            <Route path="trips" element={<Protected><TripList /></Protected>} />
            <Route path="trips/new" element={<Protected><TripNew /></Protected>} />
            <Route path="trips/:id" element={<Protected><TripDetail /></Protected>} />
            <Route path="reservations" element={<Protected><MyReservations /></Protected>} />
            <Route path="me" element={<Protected><MyProfile /></Protected>} />
            <Route path="friends" element={<Protected><FriendsPage /></Protected>} />
            <Route path="business" element={<Protected roles={["BUSINESS", "ADMIN"]}><BusinessDashboard /></Protected>} />
            <Route path="business/new" element={<Protected roles={["BUSINESS", "ADMIN"]}><NewBusinessPage /></Protected>} />
            <Route path="business/:id/edit" element={<Protected roles={["BUSINESS", "ADMIN"]}><BusinessEditPage /></Protected>} />
            <Route path="admin" element={<Protected roles={["ADMIN"]}><AdminPanel /></Protected>} />
            <Route path="*" element={<p>{t("Страницата не постои.")}</p>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>,
);
