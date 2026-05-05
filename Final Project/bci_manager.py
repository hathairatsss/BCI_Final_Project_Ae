import logging
import time
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

class BCIManager:
    def __init__(self, board_id=BoardIds.CYTON_BOARD.value, serial_port=None):
        self.board_id = board_id
        self.params = BrainFlowInputParams()
        if serial_port:
            self.params.serial_port = serial_port
            
        self.board = BoardShim(self.board_id, self.params)
        self.eeg_channels = []
        self.sampling_rate = 0
        self.is_streaming = False
        self.local_buffer = None
        self.buffer_size_seconds = 5

    def connect(self):
        BoardShim.enable_dev_board_logger()
        try:
            self.board.prepare_session()
            self.board.start_stream()
            self.eeg_channels = BoardShim.get_eeg_channels(self.board_id)
            self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
            self.is_streaming = True
            logging.warning(f"Started BrainFlow Stream. Board: {self.board_id}, Sampling Rate: {self.sampling_rate}")
            return True
        except Exception as e:
            logging.error(f"Failed to start board: {e}")
            return False

    def disconnect(self):
        if self.is_streaming:
            try:
                self.board.stop_stream()
                self.board.release_session()
                self.is_streaming = False
                logging.warning("Stopped BrainFlow Stream.")
            except Exception as e:
                logging.error(f"Error closing board: {e}")

    def get_all_data(self):
        """Returns all data accumulated since the last call to get_board_data."""
        if self.is_streaming:
            return self.board.get_board_data()
        return None
        
    def append_to_local_buffer(self, new_data):
        import numpy as np
        if self.local_buffer is None:
            self.local_buffer = new_data
        else:
            self.local_buffer = np.hstack((self.local_buffer, new_data))
            max_samples = self.sampling_rate * self.buffer_size_seconds
            if self.local_buffer.shape[1] > max_samples:
                self.local_buffer = self.local_buffer[:, -max_samples:]

    def get_recent_data(self, num_samples):
        """Returns the most recent 'num_samples' from the LOCAL buffer."""
        if self.local_buffer is not None:
            if self.local_buffer.shape[1] >= num_samples:
                return self.local_buffer[:, -num_samples:]
            else:
                return self.local_buffer
        return None
        
    def get_timestamp_channel(self):
        return BoardShim.get_timestamp_channel(self.board_id)


if __name__ == "__main__":
    # Test script to verify the BrainFlow board connection works independently
    import numpy as np
    logging.basicConfig(level=logging.INFO)
    
    print("--- BrainFlow Connection Test (Cyton 8-Channel) ---")
    port = input("Enter the COM port for your Cyton board (e.g., COM3) [Press Enter for COM3]: ").strip()
    if not port:
        port = "COM3"
        
    manager = BCIManager(board_id=BoardIds.CYTON_BOARD.value, serial_port=port)
    print(f"Testing connection to Cyton board on {port}...")
    
    if manager.connect():
        print("Connected successfully. Waiting 2 seconds for data...")
        time.sleep(2)
        data = manager.get_all_data()
        if data is not None:
            print(f"Received data shape: {data.shape}")
            print("\n--- EEG Channel Data (showing first 5 samples per channel) ---")
            for i, channel in enumerate(manager.eeg_channels):
                channel_data = data[channel]
                # Print the first 5 data points for each channel
                print(f"Channel {channel} (Index {i+1}): {np.round(channel_data[:5], 2)} ...")
            print("--------------------------------------------------------------\n")
        manager.disconnect()
        print("Test complete.")
    else:
        print("Failed to connect. Please check your COM port and Bluetooth dongle.")
        
    # Explicitly delete the manager to trigger BoardShim.__del__ before Python starts shutting down
    # This prevents the 'sys.meta_path is None' ImportError at the end of the script
    del manager


