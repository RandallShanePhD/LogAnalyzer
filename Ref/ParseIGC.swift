//
//  ParseIGC.swift
//  ParaglidingLog
//
//  Created by Randall Shane on 5/26/22.
//  Copyright © 2022 CodeIntelligence.IO. All rights reserved.
//

import Foundation

func parseIGC(fileURL: URL) -> [String: Any] {
    
    var readString = "" // Used to store the file contents
    var igcData: [String: Any] = [:]
    
    do {
        readString = try String(contentsOf: fileURL)
        let lines = readString.components(separatedBy: "\n")
        
        var rawUTCDate: String = ""
        var rawTime: String = ""
        var lastLat: Double = 0.00
        var lastLon: Double = 0.00
        var takeoffDT = Date()
        var takeoffLat: Double = 0.00
        var takeoffLon: Double = 0.00
        var takeoffAlt: Double = 0.00  // meters
        var altReadings: [Double] = []
        var highAltM = 0
        var highLiftM = 0.00
        var highSinkM = 0.00
        var distTotal = 0.00

        for line in lines {
            if line.starts(with: "HFDTE") {
                rawUTCDate = String(line.dropFirst(5))
            } else if line.starts(with: "B") {
                rawTime = String(line.prefix(7).dropFirst(1))
                var lat = Double(line.prefix(14).dropFirst(7))! / 100000.00
                let NS = line.prefix(15).dropFirst(14)
                if NS == "S" {
                    lat = lat * -1
                }

                var lon = Double(line.prefix(23).dropFirst(15))! / 100000.00
                let EW = line.prefix(24).dropFirst(23)
                if EW == "W" {
                    lon = lon * -1
                }

                // altitude, lift & sink
                var alt_m = Int(line.prefix(30).dropFirst(25)) ?? 0 // pressure alt
                
                if alt_m == 0 {
                    alt_m = Int(line.prefix(35).dropFirst(30)) ?? 0  // gps alt
                }
                
                let averagingFactor = 5
                
                if Int(rawTime)! % averagingFactor == 0 {
                    if altReadings.count > averagingFactor {
                        let climbSink = calcLiftSink(altitudes: altReadings)
                        if climbSink > highLiftM {
                            highLiftM = climbSink
                        } else if climbSink < highSinkM {
                            highSinkM = climbSink
                        }
                        altReadings = []
                    }
                } else {
                    altReadings.append(Double(alt_m))
                }
                
                
                // distance & times
                if lastLat == 0.00 && lat > 0.00 {
                    takeoffLat = lat
                    takeoffLon = lon
                    takeoffDT = convertHMtoDT(date: rawUTCDate, time: rawTime)
                    takeoffAlt = Double(alt_m)
                } else if lastLat > 0 {
                    let dist_km = haversine(lat1: lastLat, lon1: lastLon, lat2: lat, lon2: lon)
                    distTotal += abs(dist_km)
                }

                // set values
                lastLat = lat
                lastLon = lon
                if alt_m > highAltM {
                    highAltM = alt_m
                }
            }
        }
        let distFromTakeoff = haversine(lat1: takeoffLat, lon1: takeoffLon, lat2: lastLat, lon2: lastLon)
        
        // duration
        let landingDT = convertHMtoDT(date: rawUTCDate, time: rawTime)
        var flightDuration = landingDT.timeIntervalSince(takeoffDT)
        if flightDuration < 0  {
            flightDuration = flightDuration + (24 * 60 * 60)
        }
        
        
        // output
        igcData = ["lat": takeoffLat, "lon": takeoffLon, "dt": takeoffDT, "altTO": takeoffAlt, "dur": flightDuration, "distTL": distTotal, "distTO": distFromTakeoff, "alt": highAltM, "lift": highLiftM, "sink": highSinkM] as [String : Any]
        
        
    } catch let error as NSError {
        print("Failed reading IGC file: \(fileURL), Error: " + error.localizedDescription)
    }
    
    return igcData
    
}

func convertHMtoDT(date: String, time: String) -> Date {
    let dtString = "\(date) \(time)"
    let dateFormatter = DateFormatter()
    dateFormatter.dateFormat = "ddMMyy HHmmss"
    return dateFormatter.date(from: dtString)!
}

func metersToFeet(meters: Int) -> Int {
    return Int(round(Double(meters) * 3.28084))
}


func kmToMiles(km: Double) -> Double {
    return km * 0.6213712
}

func msToFpm(ms: Double) -> Double {
    return ms * 196.85
}

func calcLiftSink(altitudes: [Double]) -> Double {
    var metersPerSecond = 0.00
    var lastAltitude = Double(altitudes[0])
    var totalAltitude: Double = 0.00
    var factors: Double = 0.00
    for altitude in altitudes {
        if altitude != lastAltitude {
            factors += 1
            totalAltitude += altitude
            metersPerSecond += (altitude - lastAltitude)
            lastAltitude = altitude
        }
    }
    let altAverage: Double = metersPerSecond / factors
    return altAverage
}


func haversine(lat1: Double, lon1: Double, lat2: Double, lon2: Double) -> Double {
    // output is in M
    
    // distance between latitudes and longitudes
    let dLat = (lat2 - lat1) * Double.pi / 180.0
    let dLon = (lon2 - lon1) * Double.pi / 180.0
 
    // convert to radians
    let lat1 = (lat1) * Double.pi / 180.0
    let lat2 = (lat2) * Double.pi / 180.0
 
    // apply formulae
    let a = (pow(sin(dLat / 2), 2) + pow(sin(dLon / 2), 2) * cos(lat1) * cos(lat2));
    let rad: Double = 6371.00
    let c = 2 * asin(sqrt(a))
    return rad * c
}
