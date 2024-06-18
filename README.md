# LogAnalyzer

## TO DO:
- Detect type of flight (Thermal vs Ridge)
- Low save detector
- Add Speed to Fly / MacReady Calc
- Fix KMZ crator (adjust to ground)


## Analysis Methodology
### Default Settings
- climb_time_threshold: 10 seconds
- climb_ascend_threshold: 0.5 m/s (or you're not really climbing)
- glide_time_threshold: 15 seconds
- sink_time_threshold: 7 seconds
- sink_descend_threshold: 2.5 m/s

### Climbs
- Definition: consecutive readings greater than <climb_time_threshold>
- Efficiency Grade:
  - Each single climb is graded
  - Graded on percent of time altitude increases continuously in climbing block
  - Overall grade is the mean of all climbs grades together

### Glides
- Definition: not a climb or sink
- Efficiency Grade:
  - Calculates L/D on glide
  - Overall grade is the mean of L/Ds

### Sinks
- Definition: consecutive readings greater than <sink_time_threshold>
- Sustained more than the <sink_descend_threshold>
- Overall grade provided as a mean of sink rate

## IGC2KLM
- Came from here: 
- https://github.com/MScherbela/igc2kml
- Many Thanks!!
