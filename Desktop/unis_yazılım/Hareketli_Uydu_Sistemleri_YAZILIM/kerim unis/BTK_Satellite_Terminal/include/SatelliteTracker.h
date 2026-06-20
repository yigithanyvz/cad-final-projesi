#pragma once

#include "types.h"

class TLEParser {
public:
    static bool parse(const char* name, const char* line1, const char* line2, TLEData& tle);

private:
    static double decode_exp_field(const char* s);
};

class SGP4Propagator {
public:
    bool init(const TLEData& tle);
    bool propagate(double jd, Vec3d& r_eci, Vec3d& v_eci) const;

    static double epochToJD(double year, double day);
    static double utcToJD(int year, int month, int day, int hour, int min, double sec);

private:
    TLEData tle_{};
    SGP4Elements el_{};
    bool initialized_ = false;
};

class CoordinateTransform {
public:
    static Vec3d eciToECEF(const Vec3d& r_eci, double jd);
    static LLA ecefToLLA(const Vec3d& r);
    static AzEl calcAzEl(const LLA& observer, const Vec3d& sat_ecef_km);
    static AzEl compensatePlatformTilt(const AzEl& sat, float roll_deg, float pitch_deg);
    static Vec3d llaToECEF(const LLA& lla);
    static double gstime(double jd);
};
