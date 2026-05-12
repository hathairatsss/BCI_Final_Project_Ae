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
