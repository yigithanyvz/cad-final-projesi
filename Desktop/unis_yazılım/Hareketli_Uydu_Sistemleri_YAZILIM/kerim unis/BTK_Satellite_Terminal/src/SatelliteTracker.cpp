#include "SatelliteTracker.h"

#include "config.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kDegToRad = kPi / 180.0;
constexpr double kRadToDeg = 180.0 / kPi;
constexpr double kTwoPi = 2.0 * kPi;
constexpr double kEarthMuKm3S2 = 398600.4418;

double normalizeRad(double value) {
    value = std::fmod(value, kTwoPi);
    if (value < 0.0) value += kTwoPi;
    return value;
}

double solveKepler(double mean_anomaly, double eccentricity) {
    double E = mean_anomaly;
    for (int i = 0; i < 10; ++i) {
        const double f = E - eccentricity * std::sin(E) - mean_anomaly;
        const double fp = 1.0 - eccentricity * std::cos(E);
        if (std::fabs(fp) < 1e-12) break;
        E -= f / fp;
    }
    return E;
}

} // namespace

bool TLEParser::parse(const char* name, const char* line1, const char* line2, TLEData& tle) {
    if (!line1 || !line2 || line1[0] != '1' || line2[0] != '2') return false;

    std::strncpy(tle.name, name ? name : "", 24);
    tle.name[24] = '\0';

    tle.catalog_num = std::strtoul(line1 + 2, nullptr, 10);
    tle.classification = line1[7];
    tle.epoch_year = std::strtod(line1 + 18, nullptr);
    tle.epoch_year += tle.epoch_year < 57.0 ? 2000.0 : 1900.0;
    tle.epoch_day = std::strtod(line1 + 20, nullptr);

    char buf[16]{};
    std::strncpy(buf, line1 + 33, 10);
    tle.mean_motion_dot = std::strtod(buf, nullptr) * 2.0;

    char bstar_buf[16]{};
    std::strncpy(bstar_buf, line1 + 53, 8);
    tle.bstar = decode_exp_field(bstar_buf);

    tle.inclination_deg = std::strtod(line2 + 8, nullptr);
    tle.raan_deg = std::strtod(line2 + 17, nullptr);

    char ecc_buf[10]{};
    std::strncpy(ecc_buf, line2 + 26, 7);
    tle.eccentricity = std::strtod(ecc_buf, nullptr) * 1e-7;

    tle.arg_perigee_deg = std::strtod(line2 + 34, nullptr);
    tle.mean_anomaly_deg = std::strtod(line2 + 43, nullptr);
    tle.mean_motion_revday = std::strtod(line2 + 52, nullptr);
    tle.rev_number = std::strtoul(line2 + 63, nullptr, 10);
    tle.valid = true;
    return true;
}

double TLEParser::decode_exp_field(const char* s) {
    char mantissa[8]{};
    std::strncpy(mantissa, s, 6);
    const int exp = std::atoi(s + 6);
    return std::atof(mantissa) * std::pow(10.0, static_cast<double>(exp));
}

bool SGP4Propagator::init(const TLEData& tle) {
    if (!tle.valid || tle.mean_motion_revday <= 0.0) return false;

    tle_ = tle;
    el_.e = tle.eccentricity;
    el_.i = tle.inclination_deg * kDegToRad;
    el_.Omega = tle.raan_deg * kDegToRad;
    el_.omega = tle.arg_perigee_deg * kDegToRad;
    el_.M0 = tle.mean_anomaly_deg * kDegToRad;
    el_.n0 = tle.mean_motion_revday * kTwoPi / 86400.0;
    el_.a = std::cbrt(kEarthMuKm3S2 / (el_.n0 * el_.n0));
    el_.bstar = tle.bstar;
    el_.epoch_jd = epochToJD(tle.epoch_year, tle.epoch_day);

    initialized_ = true;
    return true;
}

bool SGP4Propagator::propagate(double jd, Vec3d& r_eci, Vec3d& v_eci) const {
    if (!initialized_) return false;

    const double dt_s = (jd - el_.epoch_jd) * 86400.0;
    const double M = normalizeRad(el_.M0 + el_.n0 * dt_s);
    const double E = solveKepler(M, el_.e);
    const double cosE = std::cos(E);
    const double sinE = std::sin(E);
    const double beta = std::sqrt(std::max(0.0, 1.0 - el_.e * el_.e));

    const double x_orb = el_.a * (cosE - el_.e);
    const double y_orb = el_.a * beta * sinE;
    const double r = el_.a * (1.0 - el_.e * cosE);

    const double factor = std::sqrt(kEarthMuKm3S2 * el_.a) / r;
    const double vx_orb = -factor * sinE;
    const double vy_orb = factor * beta * cosE;

    const double cosO = std::cos(el_.Omega);
    const double sinO = std::sin(el_.Omega);
    const double cosi = std::cos(el_.i);
    const double sini = std::sin(el_.i);
    const double cosw = std::cos(el_.omega);
    const double sinw = std::sin(el_.omega);

    const double r11 = cosO * cosw - sinO * sinw * cosi;
    const double r12 = -cosO * sinw - sinO * cosw * cosi;
    const double r21 = sinO * cosw + cosO * sinw * cosi;
    const double r22 = -sinO * sinw + cosO * cosw * cosi;
    const double r31 = sinw * sini;
    const double r32 = cosw * sini;

    r_eci.x = r11 * x_orb + r12 * y_orb;
    r_eci.y = r21 * x_orb + r22 * y_orb;
    r_eci.z = r31 * x_orb + r32 * y_orb;
    v_eci.x = r11 * vx_orb + r12 * vy_orb;
    v_eci.y = r21 * vx_orb + r22 * vy_orb;
    v_eci.z = r31 * vx_orb + r32 * vy_orb;
    return true;
}

double SGP4Propagator::epochToJD(double year, double day) {
    const int yr = static_cast<int>(year);
    const int A = yr / 100;
    const int B = 2 - A + A / 4;
    const double JD0 =
        static_cast<int>(365.25 * (yr + 4716)) +
        static_cast<int>(30.6001 * 14) +
        1.0 + B - 1524.5;
    return JD0 + day - 1.0;
}

double SGP4Propagator::utcToJD(
    int year, int month, int day,
    int hour, int min, double sec)
{
    if (month <= 2) {
        year -= 1;
        month += 12;
    }
    const int A = year / 100;
    const int B = 2 - A + A / 4;
    return static_cast<int>(365.25 * (year + 4716)) +
           static_cast<int>(30.6001 * (month + 1)) +
           day + B - 1524.5 +
           (hour + min / 60.0 + sec / 3600.0) / 24.0;
}

Vec3d CoordinateTransform::eciToECEF(const Vec3d& r_eci, double jd) {
    const double theta = gstime(jd);
    const double cos_t = std::cos(theta);
    const double sin_t = std::sin(theta);
    return {
        r_eci.x * cos_t + r_eci.y * sin_t,
        -r_eci.x * sin_t + r_eci.y * cos_t,
        r_eci.z
    };
}

LLA CoordinateTransform::ecefToLLA(const Vec3d& r) {
    constexpr double a = 6378137.0;
    constexpr double b = 6356752.3142;
    constexpr double e2 = 1.0 - (b * b) / (a * a);

    const double p = std::sqrt(r.x * r.x + r.y * r.y);
    const double lon = std::atan2(r.y, r.x);

    double lat = std::atan2(r.z, p * (1.0 - e2));
    for (int i = 0; i < 5; ++i) {
        const double sinlat = std::sin(lat);
        const double N = a / std::sqrt(1.0 - e2 * sinlat * sinlat);
        lat = std::atan2(r.z + e2 * N * sinlat, p);
    }

    const double sinlat = std::sin(lat);
    const double N = a / std::sqrt(1.0 - e2 * sinlat * sinlat);
    const double alt = p / std::cos(lat) - N;
    return {lat * kRadToDeg, lon * kRadToDeg, alt};
}

AzEl CoordinateTransform::calcAzEl(const LLA& observer, const Vec3d& sat_ecef_km) {
    const Vec3d obs = llaToECEF(observer);
    const Vec3d delta = {
        sat_ecef_km.x - obs.x,
        sat_ecef_km.y - obs.y,
        sat_ecef_km.z - obs.z
    };
    const double range =
        std::sqrt(delta.x * delta.x + delta.y * delta.y + delta.z * delta.z);
    if (range <= 0.0) return {};

    const double lat = observer.lat_deg * kDegToRad;
    const double lon = observer.lon_deg * kDegToRad;
    const double slat = std::sin(lat);
    const double clat = std::cos(lat);
    const double slon = std::sin(lon);
    const double clon = std::cos(lon);

    const double north = -slat * clon * delta.x - slat * slon * delta.y + clat * delta.z;
    const double east = -slon * delta.x + clon * delta.y;
    const double down = -clat * clon * delta.x - clat * slon * delta.y - slat * delta.z;

    const double el = std::asin(-down / range) * kRadToDeg;
    double az = std::atan2(east, north) * kRadToDeg;
    if (az < 0.0) az += 360.0;
    return {static_cast<float>(az), static_cast<float>(el), static_cast<float>(range)};
}

AzEl CoordinateTransform::compensatePlatformTilt(
    const AzEl& sat,
    float roll_deg,
    float pitch_deg)
{
    const float az_r = sat.az_deg * static_cast<float>(kDegToRad);
    const float el_r = sat.el_deg * static_cast<float>(kDegToRad);
    const float ux = std::cos(el_r) * std::sin(az_r);
    const float uy = std::cos(el_r) * std::cos(az_r);
    const float uz = std::sin(el_r);

    const float pr = pitch_deg * static_cast<float>(kDegToRad);
    const float rr = roll_deg * static_cast<float>(kDegToRad);
    const float cp = std::cos(pr);
    const float sp = std::sin(pr);
    const float cr = std::cos(rr);
    const float sr = std::sin(rr);

    const float bx = cp * ux + sp * sr * uy + sp * cr * uz;
    const float by = cr * uy - sr * uz;
    const float bz = -sp * ux + cp * sr * uy + cp * cr * uz;

    const float el_comp = std::asin(bz) * static_cast<float>(kRadToDeg);
    float az_comp = std::atan2(bx, by) * static_cast<float>(kRadToDeg);
    if (az_comp < 0.0f) az_comp += 360.0f;
    return {az_comp, el_comp, sat.range_km};
}

Vec3d CoordinateTransform::llaToECEF(const LLA& lla) {
    constexpr double a = EARTH_RADIUS_KM;
    constexpr double f = EARTH_FLATTENING;
    constexpr double e2 = 2.0 * f - f * f;

    const double lat = lla.lat_deg * kDegToRad;
    const double lon = lla.lon_deg * kDegToRad;
    const double alt = lla.alt_m / 1000.0;
    const double N = a / std::sqrt(1.0 - e2 * std::sin(lat) * std::sin(lat));

    return {
        (N + alt) * std::cos(lat) * std::cos(lon),
        (N + alt) * std::cos(lat) * std::sin(lon),
        (N * (1.0 - e2) + alt) * std::sin(lat)
    };
}

double CoordinateTransform::gstime(double jd) {
    const double tut1 = (jd - 2451545.0) / 36525.0;
    double theta =
        67310.54841 +
        (876600.0 * 3600.0 + 8640184.812866) * tut1 +
        0.093104 * tut1 * tut1 -
        6.2e-6 * tut1 * tut1 * tut1;
    theta = std::fmod(theta * kDegToRad / 240.0, kTwoPi);
    if (theta < 0.0) theta += kTwoPi;
    return theta;
}
