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
        self.eeg_channels = []

    def start(self, eeg_channels):
        try:
            self.eeg_channels = eeg_channels
            session_str = datetime.now().strftime("%Y%m%d_%H%M")
            self.filename = f"calibration_{session_str}.csv"
            self.csv_file = open(self.filename, 'w')
            
            # Header: timestamp, label, then all bands for each channel
            header = ["timestamp", "trial_label"]
            for i in range(len(eeg_channels)):
                ch_name = f"ch{i+1}"
                header.extend([f"{ch_name}_theta", f"{ch_name}_alpha", f"{ch_name}_beta", f"{ch_name}_gamma"])
            
            header.extend(["avg_beta_alpha", "avg_engagement_index"])
            
            self.csv_file.write(",".join(header) + "\n")
            logging.info(f"Started calibration logging to {self.filename}")
            return True
        except Exception as e:
            logging.error(f"Failed to open calibration CSV: {e}")
            return False

    def log_calibration_row(self, label, dashboard_payload):
        if not self.csv_file:
            return
            
        try:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            row = [ts, label]
            
            metrics = dashboard_payload["metrics"]
            avg_metrics = dashboard_payload["avg_metrics"]
            
            for i in range(len(self.eeg_channels)):
                ch_name = f"Ch {i+1}"
                if ch_name in metrics:
                    m = metrics[ch_name]
                    row.extend([
                        str(m.get("theta", 0)), 
                        str(m.get("alpha", 0)), 
                        str(m.get("beta", 0)), 
                        str(m.get("gamma", 0))
                    ])
                else:
                    row.extend(["0", "0", "0", "0"])
            
            row.append(str(avg_metrics.get("beta_alpha", 0)))
            row.append(str(avg_metrics.get("beta_theta_alpha", 0)))
            
            self.csv_file.write(",".join(row) + "\n")
            self.csv_file.flush()
        except Exception as e:
            logging.error(f"Error writing calibration row: {e}")

    def stop(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            logging.info(f"Stopped calibration logging: {self.filename}")
