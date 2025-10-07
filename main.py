import os
import threading
import messages
import router
import telemetry
import empty_pilot
import object_detector

# INIT
bee_commands = router.command_queue
stop_command = threading.Event()

# BEE-EPT (Empty pilot)
os.system('clear')
messages.display(messages.main_autopilot_started)

executor_thread = threading.Thread(target=router.command_executor, 
                                   args=[stop_command])
telemetry_thread = threading.Thread(target=telemetry.telemetry_requestor, 
                                   args=[stop_command])
empty_pilot_thread = threading.Thread(target=empty_pilot.empty_pilot_process,
                                   args=[stop_command])
object_detection_thread = threading.Thread(target=object_detector.object_detector_process,
                                   args=[stop_command])
executor_thread.start()
telemetry_thread.start()
empty_pilot_thread.start()
object_detection_thread.start()

router.put_command(router.Command(0,'INIT',{}))

input('Press enter to stop process...\n')
messages.display(messages.main_stopping_threads)

stop_command.set()

executor_thread.join()
telemetry_thread.join()
empty_pilot_thread.join()
object_detection_thread.join()

messages.display(messages.main_autopilot_finished)
