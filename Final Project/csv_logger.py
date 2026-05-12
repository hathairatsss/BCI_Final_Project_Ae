import logging
from datetime import datetime

class CSVLogger:
    def __init__(self):
        self.csv_file = None
        self.filename = ""
        
    def start(self, eeg_channels):
        try:
            session_str = datetime.now().strftime("%Y%m%d_%H%M")
            self.filename = f"session_{session_str}.csv"
            self.csv_file = open(self.filename, 'w')
            
            # Write CSV Header
            header = ["timestamp"] + [f"raw_ch{i+1}" for i in range(len(eeg_channels))] + ["attention_score"]
            self.csv_file.write(",".join(header) + "\n")
            logging.info(f"Started logging to {self.filename}")
            return True
        except Exception as e:
            logging.error(f"Failed to open CSV file: {e}")
            return False

    def log_data(self, new_data, num_samples, timestamp_channel, eeg_channels, attention_score):
        if not self.csv_file:
            return
            
        try:
            for i in range(num_samples):
                ts = new_data[timestamp_channel, i]
                row_data = [str(ts)]
                for ch in eeg_channels:
                    row_data.append(str(new_data[ch, i]))
                row_data.append(str(attention_score))
                self.csv_file.write(",".join(row_data) + "\n")
            self.csv_file.flush()
        except Exception as e:
            logging.error(f"Error writing to CSV: {e}")

    def stop(self):
        if self.csv_file:
            try:
                self.csv_file.close()
                self.csv_file = None
                logging.info(f"Closed CSV file {self.filename}")
            except Exception as e:
                logging.error(f"Error closing CSV file: {e}")

class CalibrationLogger:
    def __init__(self):
        self.csv_file = None
        self.filename = ""
        self.is_recording = False
        self.label = ""
        
    def start(self, label, eeg_channels):
        if self.is_recording:
            return False
        try:
            self.label = label
            session_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filename = f"calibration_{label}_{session_str}.csv"
            self.csv_file = open(self.filename, 'w')
            
            # Write CSV Header
            header = ["timestamp", "label"]
            for i in range(len(eeg_channels)):
                ch_prefix = f"ch{i+1}"
                header.extend([
                    f"{ch_prefix}_theta", f"{ch_prefix}_alpha", f"{ch_prefix}_beta", f"{ch_prefix}_gamma",
                    f"{ch_prefix}_beta_alpha", f"{ch_prefix}_beta_theta_alpha", f"{ch_prefix}_one_over_alpha", f"{ch_prefix}_rms"
                ])
            header.extend(["avg_beta_alpha", "avg_beta_theta_alpha", "avg_one_over_alpha"])
            self.csv_file.write(",".join(header) + "\n")
            
            self.is_recording = True
            logging.info(f"Started Calibration recording to {self.filename}")
            return True
        except Exception as e:
            logging.error(f"Failed to open Calibration CSV file: {e}")
            return False

    def log_metrics(self, timestamp, payload):
        if not self.is_recording or not self.csv_file:
            return
            
        try:
            row_data = [str(timestamp), self.label]
            
            # Expecting payload format from process_dashboard_data
            metrics = payload.get("metrics", {})
            for ch_name, m in metrics.items():
                row_data.extend([
                    str(m.get("theta", 0)), str(m.get("alpha", 0)), str(m.get("beta", 0)), str(m.get("gamma", 0)),
                    str(m.get("beta_alpha", 0)), str(m.get("beta_theta_alpha", 0)), str(m.get("one_over_alpha", 0)), str(m.get("rms", 0))
                ])
                
            avg_m = payload.get("avg_metrics", {})
            row_data.extend([
                str(avg_m.get("beta_alpha", 0)), str(avg_m.get("beta_theta_alpha", 0)), str(avg_m.get("one_over_alpha", 0))
            ])
            
            self.csv_file.write(",".join(row_data) + "\n")
            self.csv_file.flush()
        except Exception as e:
            logging.error(f"Error writing to Calibration CSV: {e}")

    def stop(self):
        if self.csv_file:
            try:
                self.csv_file.close()
                self.csv_file = None
                self.is_recording = False
                logging.info(f"Closed Calibration CSV file {self.filename}")
            except Exception as e:
                logging.error(f"Error closing Calibration CSV file: {e}")
