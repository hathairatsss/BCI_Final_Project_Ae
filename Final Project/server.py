import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from brainflow.board_shim import BoardIds
from bci_manager import BCIManager
from signal_processing import process_eeg_data
from csv_logger import CSVLogger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- CONFIGURATION -----------------
STREAM_HZ = 10 # 10Hz to frontend

# Global components
bci_manager = BCIManager(board_id=BoardIds.CYTON_BOARD.value, serial_port='COM3')
csv_logger = CSVLogger()

@app.on_event("startup")
async def startup_event():
    if bci_manager.connect():
        csv_logger.start(bci_manager.eeg_channels)
    else:
        logging.error("Failed to initialize BCI Manager on startup.")

@app.on_event("shutdown")
async def shutdown_event():
    bci_manager.disconnect()
    csv_logger.stop()

@app.websocket("/ws/attention")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.warning("Frontend connected to WebSocket.")
    try:
        while True:
            # Variables for this iteration
            attention_score = 0.5
            current_alpha = 0.0
            current_beta = 0.0
            
            # 1. Get chunk for CSV
            new_data = bci_manager.get_all_data()
            
            if new_data is not None:
                num_samples = new_data.shape[1]
                if num_samples > 0:
                    # Get a slightly larger window for processing PSD (e.g., last 2 seconds)
                    window_data = bci_manager.get_recent_data(bci_manager.sampling_rate * 2) 
                    
                    # Process Attention Score
                    if window_data is not None:
                        attention_score, current_alpha, current_beta = process_eeg_data(
                            window_data, 
                            bci_manager.eeg_channels, 
                            bci_manager.sampling_rate
                        )
                    
                    # Write to CSV
                    csv_logger.log_data(
                        new_data, 
                        num_samples, 
                        bci_manager.get_timestamp_channel(), 
                        bci_manager.eeg_channels, 
                        attention_score
                    )
                
            # Send to frontend
            payload = {
                "attention_score": float(attention_score),
                "alpha": float(current_alpha),
                "beta": float(current_beta)
            }
            await websocket.send_text(json.dumps(payload))
            
            # Wait for next tick (10Hz)
            await asyncio.sleep(1.0 / STREAM_HZ)
            
    except WebSocketDisconnect:
        logging.warning("Frontend disconnected.")
    except Exception as e:
        logging.error(f"WebSocket Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
