# LogAnalyzer

## Analysis Methodology
### Default Settings
- climb_time_threshold: 10 seconds
- climb_ascend_threshold: 0.5 m/s (or you're not really climbing)
- glide_time_threshold: 15 seconds
- sink_time_threshold: 7 seconds
- sink_descend_threshold: 2.5 m/s

### Climbs
- Definition: consecutive readings greater than <climb_time_threshold>
- Sustained more than 1/3rd of the time over the <climb_ascend_threshold>
- Efficiency Grade:
  - Each single climb is graded: number of climbing readings > 0 / total number of readings in the climb
  - Overall grade is the mean of all climbs grades together

### Glides
- Definition: consecutive readings greater than <glide_time_threshold>
- Efficiency Grade:
  - Each single climb is graded: number of gliding readings > <sink_descend_threshold> / total number of readings
  - Overall grade is the mean of all glide grades together

### Sinks
- Definition: consecutive readings greater than <sink_time_threshold>
- Sustained more than the <sink_descend_threshold>
- Provided as a number of recorded sinking glides
