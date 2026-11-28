"""Import the verified 80 Claim Department Multiple Choice Questions and provision roster candidates."""
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal, Base, engine, run_advisory_lock_migration
from backend.app.models.models import Assessment, Section, Question, Option, Roster, Attempt, Answer, Violation, Snapshot, Event, Restart

CLAIM_CANDIDATES = [
    {"code": "E-1304001", "name": "Umesh Pradeep Devare", "dept": "CLAIM"},
    {"code": "E-1507005", "name": "Prasad Morje", "dept": "CLAIM"},
    {"code": "E-2312031", "name": "Shifa Qureshi", "dept": "CLAIM"},
]

CLAIM_QUESTIONS = [
    # --- Nephrology (Q1 - Q14) ---
    {
        "section": "Nephrology",
        "num": 1,
        "stem": "What most commonly causes the urinary obstruction responsible for renal colic?",
        "options": [
            ("A", "Autoimmune inflammation of the kidney"),
            ("B", "Permanent loss of kidney filtration"),
            ("C", "An ascending kidney infection"),
            ("D", "A urinary or kidney stone")
        ],
        "correct": "D"
    },
    {
        "section": "Nephrology",
        "num": 2,
        "stem": "Over what time frame does acute kidney injury typically develop?",
        "options": [
            ("A", "Over hours to days"),
            ("B", "Over several months"),
            ("C", "Over several years"),
            ("D", "Only after lifelong kidney disease")
        ],
        "correct": "A"
    },
    {
        "section": "Nephrology",
        "num": 3,
        "stem": "Which structure acts as the natural filter during peritoneal dialysis?",
        "options": [
            ("A", "The peritoneal membrane"),
            ("B", "An external dialyzer"),
            ("C", "The urinary bladder"),
            ("D", "The renal pelvis")
        ],
        "correct": "A"
    },
    {
        "section": "Nephrology",
        "num": 4,
        "stem": "A patient with sudden kidney failure receives short-term blood filtration through an external machine while kidney function recovers. Which treatment best matches this description?",
        "options": [
            ("A", "Chronic haemodialysis for permanent failure"),
            ("B", "Acute haemodialysis for kidney injury"),
            ("C", "Antibiotic treatment for pyelonephritis"),
            ("D", "Peritoneal dialysis through the abdomen")
        ],
        "correct": "B"
    },
    {
        "section": "Nephrology",
        "num": 5,
        "stem": "Which condition generally requires long-term haemodialysis?",
        "options": [
            ("A", "A brief reduction in urine output without kidney failure"),
            ("B", "An isolated infection with preserved kidney function"),
            ("C", "Transient pain from a urinary stone"),
            ("D", "End-stage renal disease with permanent kidney failure")
        ],
        "correct": "D"
    },
    {
        "section": "Nephrology",
        "num": 6,
        "stem": "Which description best matches continuous renal replacement therapy?",
        "options": [
            ("A", "A short, isolated blood-filtration session without continuous support"),
            ("B", "Abdominal dialysis using the peritoneal membrane as a natural filter"),
            ("C", "Intermittent, long-term dialysis in patients with permanent kidney failure"),
            ("D", "Slow, continuous dialysis in critically ill patients with acute kidney injury")
        ],
        "correct": "D"
    },
    {
        "section": "Nephrology",
        "num": 7,
        "stem": "Which record most directly documents the treatment delivered during a dialysis session?",
        "options": [
            ("A", "A dialysis chart"),
            ("B", "A drug batch register"),
            ("C", "A temperature-only chart"),
            ("D", "A surgical consent form")
        ],
        "correct": "A"
    },
    {
        "section": "Nephrology",
        "num": 8,
        "stem": "Which set of details combines patient identification, the treatment date and clinician authentication on a dialysis chart?",
        "options": [
            ("A", "Date, time, bed number and diagnosis"),
            ("B", "Name, age, address and signature"),
            ("C", "Name, photograph, ward number and date"),
            ("D", "Name, date, signature and stamp")
        ],
        "correct": "D"
    },
    {
        "section": "Nephrology",
        "num": 9,
        "stem": "What is pyelonephritis?",
        "options": [
            ("A", "A permanent loss of all kidney function"),
            ("B", "A bacterial infection of the renal pelvis and kidney tissue"),
            ("C", "An autoimmune injury caused by systemic lupus"),
            ("D", "A blockage caused by a urinary stone")
        ],
        "correct": "B"
    },
    {
        "section": "Nephrology",
        "num": 10,
        "stem": "Which urine investigation identifies the infecting organism and helps guide antibiotic selection in pyelonephritis?",
        "options": [
            ("A", "Urine culture and sensitivity"),
            ("B", "Urine cytology"),
            ("C", "Urine ketone testing"),
            ("D", "Urine pregnancy testing")
        ],
        "correct": "A"
    },
    {
        "section": "Nephrology",
        "num": 11,
        "stem": "Which pair of methods can quantify protein loss in the urine in glomerular disease?",
        "options": [
            ("A", "A 24-hour urine protein collection or a spot urine protein-to-creatinine ratio"),
            ("B", "A blood pressure reading or a pulse measurement"),
            ("C", "A kidney ultrasound or a bladder ultrasound"),
            ("D", "A urine culture or a urine antibiotic sensitivity test")
        ],
        "correct": "A"
    },
    {
        "section": "Nephrology",
        "num": 12,
        "stem": "Which detail provides batch-level traceability for Rituximab used in a patient's treatment?",
        "options": [
            ("A", "The premedication and observation chart"),
            ("B", "The prescribed dose and administration time"),
            ("C", "The drug barcode or batch information"),
            ("D", "The infusion rate and treatment duration")
        ],
        "correct": "C"
    },
    {
        "section": "Nephrology",
        "num": 13,
        "stem": "Which underlying disease causes lupus nephritis?",
        "options": [
            ("A", "Ascending bacterial urinary tract infection"),
            ("B", "Systemic lupus erythematosus"),
            ("C", "Urinary stone obstruction"),
            ("D", "Ureteropelvic junction obstruction")
        ],
        "correct": "B"
    },
    {
        "section": "Nephrology",
        "num": 14,
        "stem": "Which investigation confirms the specific class and histological severity of lupus nephritis?",
        "options": [
            ("A", "A urine protein measurement"),
            ("B", "A serum creatinine measurement"),
            ("C", "A kidney biopsy"),
            ("D", "A kidney ultrasound")
        ],
        "correct": "C"
    },

    # --- Paediatric Surgery (Q15 - Q28) ---
    {
        "section": "Paediatric Surgery",
        "num": 15,
        "stem": "Which problem does Ladd's procedure treat?",
        "options": [
            ("A", "Abnormal intestinal positioning with a risk of twisting or blockage"),
            ("B", "A narrowing where the renal pelvis joins the ureter"),
            ("C", "Backward flow of urine toward the kidneys"),
            ("D", "An abnormal connection between the airway and food pipe")
        ],
        "correct": "A"
    },
    {
        "section": "Paediatric Surgery",
        "num": 16,
        "stem": "What is the main purpose of open ureteric reimplantation?",
        "options": [
            ("A", "Remove a narrowed segment at the kidney pelvis outlet"),
            ("B", "Reattach the ureter to the bladder to prevent backward urine flow"),
            ("C", "Join two healthy ureteric ends to restore their continuity"),
            ("D", "Create a bladder opening through the lower abdominal skin")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 17,
        "stem": "Which structures are joined in an open uretero-ureterostomy?",
        "options": [
            ("A", "The stomach and pancreatic pseudocyst"),
            ("B", "The trachea and esophagus"),
            ("C", "The bladder and lower abdominal skin"),
            ("D", "Two healthy ends of the ureter")
        ],
        "correct": "D"
    },
    {
        "section": "Paediatric Surgery",
        "num": 18,
        "stem": "Which obstruction can be treated by either open or laparoscopic pyeloplasty?",
        "options": [
            ("A", "An obstruction at the bladder-to-urethra outlet"),
            ("B", "An obstruction within the lower large intestine"),
            ("C", "An obstruction where the renal pelvis joins the ureter"),
            ("D", "An obstruction at the stomach-to-small-intestine outlet")
        ],
        "correct": "C"
    },
    {
        "section": "Paediatric Surgery",
        "num": 19,
        "stem": "Which pair combines ultrasound with imaging of the bladder and urethra when assessing a child for vesicostomy?",
        "options": [
            ("A", "Ultrasonography and a cystourethrogram"),
            ("B", "CT-IVP and an MRI urogram"),
            ("C", "Intravenous pyelography and a DTPA renal scan"),
            ("D", "Kidney biopsy and urine culture")
        ],
        "correct": "A"
    },
    {
        "section": "Paediatric Surgery",
        "num": 20,
        "stem": "Which connection is created during a vesicostomy?",
        "options": [
            ("A", "The pancreatic pseudocyst to the stomach"),
            ("B", "The urinary bladder to the lower abdominal skin"),
            ("C", "The jejunum to a feeding tube"),
            ("D", "The renal pelvis to the ureter")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 21,
        "stem": "What is the purpose of the bladder-to-skin pathway created by an appendicovesicostomy or Monti procedure?",
        "options": [
            ("A", "To deliver feeding solution directly into the small intestine"),
            ("B", "To empty the bladder using a catheter through the new opening"),
            ("C", "To close a former feeding opening in the abdominal wall"),
            ("D", "To drain a pancreatic pseudocyst into the stomach")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 22,
        "stem": "A tracheo-esophageal fistula is an abnormal connection between which structures?",
        "options": [
            ("A", "The kidney and bladder"),
            ("B", "The stomach and jejunum"),
            ("C", "The pancreas and stomach"),
            ("D", "The trachea and esophagus")
        ],
        "correct": "D"
    },
    {
        "section": "Paediatric Surgery",
        "num": 23,
        "stem": "Where is the feeding tube placed in a feeding jejunostomy?",
        "options": [
            ("A", "Directly into the colon"),
            ("B", "Directly into the jejunum"),
            ("C", "Directly into the stomach"),
            ("D", "Directly into the esophagus")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 24,
        "stem": "What is the main purpose of operative gastrostomy?",
        "options": [
            ("A", "Drain urine through an opening in the lower abdominal skin"),
            ("B", "Provide nutrition through a tube placed directly into the stomach"),
            ("C", "Drain a pancreatic pseudocyst by joining it to the stomach"),
            ("D", "Restore urine flow by reconnecting the renal pelvis and ureter")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 25,
        "stem": "What does cystogastrostomy allow to drain into the stomach?",
        "options": [
            ("A", "The contents of the pancreatic duct"),
            ("B", "The contents of the common bile duct"),
            ("C", "The contents of a pancreatic pseudocyst"),
            ("D", "The contents of the gallbladder")
        ],
        "correct": "C"
    },
    {
        "section": "Paediatric Surgery",
        "num": 26,
        "stem": "When is gastrostomy closure appropriate?",
        "options": [
            ("A", "When backward urine flow needs to be corrected"),
            ("B", "When the gastrostomy feeding tube is no longer required"),
            ("C", "When a pancreatic pseudocyst requires internal drainage"),
            ("D", "When a new feeding route into the stomach is first required")
        ],
        "correct": "B"
    },
    {
        "section": "Paediatric Surgery",
        "num": 27,
        "stem": "Which action is performed in pyloromyotomy?",
        "options": [
            ("A", "Closing the stomach-to-abdominal-wall opening"),
            ("B", "Joining two healthy ends of the ureter"),
            ("C", "Dividing the pyloric muscle to relieve obstruction"),
            ("D", "Removing abnormal intestinal bands")
        ],
        "correct": "C"
    },
    {
        "section": "Paediatric Surgery",
        "num": 28,
        "stem": "Which postoperative investigation can assess the repaired esophageal passage using contrast after tracheo-esophageal fistula repair?",
        "options": [
            ("A", "A postoperative esophageal endoscopy"),
            ("B", "A postoperative abdominal ultrasound"),
            ("C", "A postoperative dye study"),
            ("D", "A postoperative plain chest X-ray")
        ],
        "correct": "C"
    },

    # --- Neurosurgery (Q29 - Q38) ---
    {
        "section": "Neurosurgery",
        "num": 29,
        "stem": "Which description best matches burr hole surgery?",
        "options": [
            ("A", "Placing a metal clip at the base of a cerebral aneurysm"),
            ("B", "Passing a catheter into a vessel for cerebral angiography"),
            ("C", "Making a small opening in the skull to access the area beneath it"),
            ("D", "Removing a large skull bone flap to expose the brain")
        ],
        "correct": "C"
    },
    {
        "section": "Neurosurgery",
        "num": 30,
        "stem": "What is the purpose of external ventricular drainage?",
        "options": [
            ("A", "Removing a post-traumatic blood collection from brain tissue"),
            ("B", "Draining excess cerebrospinal fluid and/or monitoring intracranial pressure"),
            ("C", "Removing a cervical disc and fusing adjacent vertebrae"),
            ("D", "Closing a cerebral aneurysm and confirming clip position")
        ],
        "correct": "B"
    },
    {
        "section": "Neurosurgery",
        "num": 31,
        "stem": "A post-traumatic intraparenchymal hematoma is a collection of blood in which location?",
        "options": [
            ("A", "Between the dura and arachnoid"),
            ("B", "Between the skull and dura"),
            ("C", "Within the subarachnoid space"),
            ("D", "Within the brain tissue")
        ],
        "correct": "D"
    },
    {
        "section": "Neurosurgery",
        "num": 32,
        "stem": "Which condition can be treated with a ventriculoperitoneal shunt?",
        "options": [
            ("A", "Hemifacial spasm"),
            ("B", "Lumbar disc herniation"),
            ("C", "Hydrocephalus"),
            ("D", "Trigeminal neuralgia")
        ],
        "correct": "C"
    },
    {
        "section": "Neurosurgery",
        "num": 33,
        "stem": "Which pair of disorders may be treated with microvascular decompression?",
        "options": [
            ("A", "Brain stem tumour and spinal intradural hematoma"),
            ("B", "Cervical disc herniation and lumbar disc herniation"),
            ("C", "Hydrocephalus and intracranial hematoma"),
            ("D", "Trigeminal neuralgia and hemifacial spasm")
        ],
        "correct": "D"
    },
    {
        "section": "Neurosurgery",
        "num": 34,
        "stem": "An aneurysm-clipping claim file contains postoperative imaging, operative notes and a discharge summary. Which invoice best substantiates the devices used for clipping?",
        "options": [
            ("A", "Invoice for embolization coils"),
            ("B", "Invoice for cervical fusion implants"),
            ("C", "Invoice for an RF probe"),
            ("D", "Invoice for all clips used")
        ],
        "correct": "D"
    },
    {
        "section": "Neurosurgery",
        "num": 35,
        "stem": "What sequence best describes anterior cervical discectomy and fusion?",
        "options": [
            ("A", "Remove a damaged cervical disc and fuse surrounding vertebrae"),
            ("B", "Remove a damaged lumbar disc and fuse surrounding vertebrae"),
            ("C", "Fuse the cervical vertebrae without removing the damaged disc"),
            ("D", "Remove a damaged cervical disc and leave the vertebrae unfused")
        ],
        "correct": "A"
    },
    {
        "section": "Neurosurgery",
        "num": 36,
        "stem": "What is removed during lumbar discectomy?",
        "options": [
            ("A", "An entire lumbar vertebral body compressing a nerve"),
            ("B", "A blood collection from within the spinal canal"),
            ("C", "The portion of a damaged lower-back disc pressing on a spinal nerve"),
            ("D", "The portion of a damaged cervical disc pressing on a spinal nerve")
        ],
        "correct": "C"
    },
    {
        "section": "Neurosurgery",
        "num": 37,
        "stem": "What is the main imaging target of diagnostic cerebral or spinal digital subtraction angiography?",
        "options": [
            ("A", "Blood vessels of the brain or spinal cord"),
            ("B", "Intervertebral discs of the cervical and lumbar spine"),
            ("C", "White-matter tracts within the brain"),
            ("D", "Ventricular cavities containing cerebrospinal fluid")
        ],
        "correct": "A"
    },
    {
        "section": "Neurosurgery",
        "num": 38,
        "stem": "A brain stem tumour arises in which anatomical region?",
        "options": [
            ("A", "Peripheral nerves outside the skull"),
            ("B", "The lumbar spinal canal"),
            ("C", "The frontal cerebral hemisphere"),
            ("D", "The lower part of the brain connecting to the spinal cord")
        ],
        "correct": "D"
    },

    # --- Polytrauma (Q39 - Q52) ---
    {
        "section": "Polytrauma",
        "num": 39,
        "stem": "Which scenario best fits the definition of polytrauma?",
        "options": [
            ("A", "Minor limb injuries sustained in separate unrelated incidents"),
            ("B", "A serious head injury with a superficial cut on the scalp"),
            ("C", "Serious head and chest injuries sustained in the same accident"),
            ("D", "Multiple superficial abrasions without serious organ or regional injury")
        ],
        "correct": "C"
    },
    {
        "section": "Polytrauma",
        "num": 40,
        "stem": "Which approach represents conservative management of an abdominal injury?",
        "options": [
            ("A", "Abdominal organ resection with postoperative monitoring"),
            ("B", "Observation, investigations, monitoring and supportive treatment"),
            ("C", "Laparoscopic exploration with abdominal organ repair"),
            ("D", "Immediate laparotomy with abdominal injury repair")
        ],
        "correct": "B"
    },
    {
        "section": "Polytrauma",
        "num": 41,
        "stem": "When documenting surgery for a patient with chest injury and long-bone fractures, which detail best describes the extent of fracture fixation?",
        "options": [
            ("A", "The anatomical site of the chest injury"),
            ("B", "The duration of respiratory symptoms"),
            ("C", "The number of long bones requiring fixation"),
            ("D", "The type of anaesthesia used")
        ],
        "correct": "C"
    },
    {
        "section": "Polytrauma",
        "num": 42,
        "stem": "A patient requires surgery for a visceral injury and operative stabilization of a single long-bone fracture. Which combination addresses both treatment needs?",
        "options": [
            ("A", "Surgical treatment of the visceral injury and observation of the fracture"),
            ("B", "Surgical treatment of the visceral injury and fixation of the fracture"),
            ("C", "Observation of the visceral injury and observation of the fracture"),
            ("D", "Observation of the visceral injury and fixation of the fracture")
        ],
        "correct": "B"
    },
    {
        "section": "Polytrauma",
        "num": 43,
        "stem": "Which record best explains the planned conservative treatment of a severe head injury before authorization?",
        "options": [
            ("A", "Operative notes describing a completed procedure"),
            ("B", "An invoice documenting the implants used"),
            ("C", "A discharge summary detailing the completed admission"),
            ("D", "Clinical notes with the planned line of treatment")
        ],
        "correct": "D"
    },
    {
        "section": "Polytrauma",
        "num": 44,
        "stem": "A patient requires evacuation of a subdural hematoma and operative stabilization of a long-bone fracture. Which combination addresses both needs?",
        "options": [
            ("A", "Craniotomy with hematoma evacuation and tendon reconstruction"),
            ("B", "Cerebral aneurysm clipping and long-bone fracture fixation"),
            ("C", "Craniotomy with hematoma evacuation and long-bone fracture fixation"),
            ("D", "Ventricular shunt placement and long-bone fracture fixation")
        ],
        "correct": "C"
    },
    {
        "section": "Polytrauma",
        "num": 45,
        "stem": "Which visual record most directly demonstrates that a tendon or peripheral nerve repair was performed?",
        "options": [
            ("A", "A preoperative clinical photograph of the injured limb"),
            ("B", "A preoperative radiograph of an associated bone fracture"),
            ("C", "A postoperative clinical photograph of the healed scar"),
            ("D", "An intraoperative photograph showing the tendon or nerve repair")
        ],
        "correct": "D"
    },
    {
        "section": "Polytrauma",
        "num": 46,
        "stem": "What does EMG stand for in the assessment of nerve plexus or tendon injuries?",
        "options": [
            ("A", "Vascular Doppler ultrasonography"),
            ("B", "Electroencephalography"),
            ("C", "Electromyography"),
            ("D", "Nerve conduction study")
        ],
        "correct": "C"
    },
    {
        "section": "Polytrauma",
        "num": 47,
        "stem": "When a plexus injury is accompanied by vascular injury, which additional intervention directly addresses the vascular injury?",
        "options": [
            ("A", "Vascular repair or grafting"),
            ("B", "Tendon repair"),
            ("C", "Wound exploration and closure"),
            ("D", "Nerve grafting")
        ],
        "correct": "A"
    },
    {
        "section": "Polytrauma",
        "num": 48,
        "stem": "Which discharge-card content provides evidence of care actually delivered for a corneal foreign body?",
        "options": [
            ("A", "Evidence of investigations and treatment performed"),
            ("B", "The provisional diagnosis and future treatment plan only"),
            ("C", "The admission findings without the investigation results"),
            ("D", "The follow-up schedule without the treatment details")
        ],
        "correct": "A"
    },
    {
        "section": "Polytrauma",
        "num": 49,
        "stem": "What is the term for stitching a postoperative wound gap closed again?",
        "options": [
            ("A", "Debridement"),
            ("B", "Resuturing"),
            ("C", "Flap-cover surgery"),
            ("D", "Skin grafting")
        ],
        "correct": "B"
    },
    {
        "section": "Polytrauma",
        "num": 50,
        "stem": "Which photograph pair best documents the immediate change produced by wound-gap resuturing?",
        "options": [
            ("A", "During surgery and after discharge"),
            ("B", "During surgery and at final follow-up"),
            ("C", "Before surgery and immediately after surgery"),
            ("D", "Before surgery and at final follow-up")
        ],
        "correct": "C"
    },
    {
        "section": "Polytrauma",
        "num": 51,
        "stem": "Which combined procedure stabilizes a compound fracture and uses a flap to cover its associated wound?",
        "options": [
            ("A", "Internal fixation with nerve grafting"),
            ("B", "Internal fixation with flap-cover surgery"),
            ("C", "Internal fixation with wound resuturing alone"),
            ("D", "Internal fixation with tendon transfer")
        ],
        "correct": "B"
    },
    {
        "section": "Polytrauma",
        "num": 52,
        "stem": "At which stage should initial patient stabilization occur in relation to planned internal fixation of a long-bone fracture?",
        "options": [
            ("A", "After completing fracture rehabilitation"),
            ("B", "After fracture union is documented"),
            ("C", "Before internal fixation"),
            ("D", "Immediately before hospital discharge")
        ],
        "correct": "C"
    },

    # --- Pulmonology (Q53 - Q62) ---
    {
        "section": "Pulmonology",
        "num": 53,
        "stem": "Which pair of conditions is commonly associated with chronic obstructive pulmonary disease (COPD)?",
        "options": [
            ("A", "Chronic bronchitis and emphysema"),
            ("B", "Pneumothorax and pleural effusion"),
            ("C", "Empyema and haemothorax"),
            ("D", "Pneumoconiosis and pulmonary embolism")
        ],
        "correct": "A"
    },
    {
        "section": "Pulmonology",
        "num": 54,
        "stem": "What is the main purpose of intercostal drainage?",
        "options": [
            ("A", "To remove an endobronchial growth through a scope"),
            ("B", "To remove abnormal air or fluid from the pleural space"),
            ("C", "To obtain a tissue sample from the bronchial wall"),
            ("D", "To measure airflow during forced expiration")
        ],
        "correct": "B"
    },
    {
        "section": "Pulmonology",
        "num": 55,
        "stem": "For COPD pre-authorisation, which document records the patient's vital signs and examination findings on admission?",
        "options": [
            ("A", "Post-treatment laboratory reports"),
            ("B", "Detailed discharge summary"),
            ("C", "Discharge photograph"),
            ("D", "Admission notes")
        ],
        "correct": "D"
    },
    {
        "section": "Pulmonology",
        "num": 56,
        "stem": "Which route is used to introduce a flexible bronchoscope into the airways?",
        "options": [
            ("A", "Through the nose or mouth into the trachea and bronchi"),
            ("B", "Through a blood vessel into the pulmonary artery"),
            ("C", "Through the chest wall into the pleural cavity"),
            ("D", "Through the nose or mouth into the oesophagus and stomach")
        ],
        "correct": "A"
    },
    {
        "section": "Pulmonology",
        "num": 57,
        "stem": "Which exposure history most directly supports a diagnosis of pneumoconiosis?",
        "options": [
            ("A", "Long-term occupational exposure to dust"),
            ("B", "Recent exposure to a respiratory infection"),
            ("C", "Long-term tobacco smoking"),
            ("D", "Repeated seasonal exposure to pollen")
        ],
        "correct": "A"
    },
    {
        "section": "Pulmonology",
        "num": 58,
        "stem": "Which investigation measures lung capacity and airflow?",
        "options": [
            ("A", "Chest X-ray"),
            ("B", "Bronchoscopy with biopsy"),
            ("C", "Pulmonary function test"),
            ("D", "High-resolution CT of the chest")
        ],
        "correct": "C"
    },
    {
        "section": "Pulmonology",
        "num": 59,
        "stem": "Which investigation provides detailed cross-sectional images of lung changes in pneumoconiosis?",
        "options": [
            ("A", "Chest X-ray"),
            ("B", "Bronchoscopy with biopsy"),
            ("C", "Pulmonary function test"),
            ("D", "High-resolution CT of the chest")
        ],
        "correct": "D"
    },
    {
        "section": "Pulmonology",
        "num": 60,
        "stem": "What is the main purpose of therapeutic bronchoscopy with excisional intervention?",
        "options": [
            ("A", "It removes abnormal tissue or obstructing material from the airways"),
            ("B", "It measures lung volumes during a breathing test"),
            ("C", "It drains fluid from the pleural cavity through a chest tube"),
            ("D", "It creates a permanent opening through the chest wall")
        ],
        "correct": "A"
    },
    {
        "section": "Pulmonology",
        "num": 61,
        "stem": "Which pair of records best documents a completed therapeutic bronchoscopy with excisional intervention for a claim?",
        "options": [
            ("A", "Clinical history and proposed management plan"),
            ("B", "Occupational history and baseline chest X-ray"),
            ("C", "Admission notes and planned investigations"),
            ("D", "Procedure notes and endoscopic video")
        ],
        "correct": "D"
    },
    {
        "section": "Pulmonology",
        "num": 62,
        "stem": "What does a TPR chart record?",
        "options": [
            ("A", "Temperature, pain and respiration"),
            ("B", "Temperature, pressure and respiration"),
            ("C", "Temperature, pulse and respiration"),
            ("D", "Temperature, pulse and reflexes")
        ],
        "correct": "C"
    },

    # --- Interventional Radiology (Q63 - Q80) ---
    {
        "section": "Interventional Radiology",
        "num": 63,
        "stem": "Which description best matches interventional radiology?",
        "options": [
            ("A", "Electrical recording of heart and brain activity"),
            ("B", "Image-guided minimally invasive diagnosis and treatment"),
            ("C", "Open surgery performed through a large incision"),
            ("D", "Microscopic examination of surgically removed tissue")
        ],
        "correct": "B"
    },
    {
        "section": "Interventional Radiology",
        "num": 64,
        "stem": "What is the purpose of balloon test occlusion?",
        "options": [
            ("A", "To dissolve a cerebral clot with thrombolytic medicine"),
            ("B", "To leave a permanent scaffold within a narrowed artery"),
            ("C", "To assess whether the brain can tolerate permanent vessel closure"),
            ("D", "To fill an aneurysm permanently with embolization coils")
        ],
        "correct": "C"
    },
    {
        "section": "Interventional Radiology",
        "num": 65,
        "stem": "Which procedure uses a balloon to widen a narrowed artery and restore blood flow?",
        "options": [
            ("A", "Vascular plug embolization"),
            ("B", "Balloon test occlusion"),
            ("C", "Arterial angioplasty"),
            ("D", "Coil embolization")
        ],
        "correct": "C"
    },
    {
        "section": "Interventional Radiology",
        "num": 66,
        "stem": "Which route is used to insert a peripherally inserted central catheter (PICC)?",
        "options": [
            ("A", "From a femoral artery into the aorta"),
            ("B", "From an arm vein into a large central vein"),
            ("C", "From the internal jugular vein into a hepatic vein"),
            ("D", "From a radial artery into a cerebral artery")
        ],
        "correct": "B"
    },
    {
        "section": "Interventional Radiology",
        "num": 67,
        "stem": "Percutaneous cholangioplasty uses a balloon catheter to widen which structure?",
        "options": [
            ("A", "A narrowed central vein"),
            ("B", "A narrowed bile duct"),
            ("C", "A narrowed carotid artery"),
            ("D", "A narrowed ureter")
        ],
        "correct": "B"
    },
    {
        "section": "Interventional Radiology",
        "num": 68,
        "stem": "Which embolic material provides temporary vessel blockage to control bleeding?",
        "options": [
            ("A", "Gelfoam particles or pledgets"),
            ("B", "Medical alcohol"),
            ("C", "A vascular plug"),
            ("D", "Embolization coils")
        ],
        "correct": "A"
    },
    {
        "section": "Interventional Radiology",
        "num": 69,
        "stem": "What is the main function of an inferior vena cava (IVC) filter?",
        "options": [
            ("A", "To dissolve an existing leg-vein clot with medicine"),
            ("B", "To catch migrating clots before they reach the lungs"),
            ("C", "To widen a narrowed deep vein with a balloon"),
            ("D", "To remove a cerebral artery clot using suction")
        ],
        "correct": "B"
    },
    {
        "section": "Interventional Radiology",
        "num": 70,
        "stem": "What two actions are combined in conventional transarterial chemoembolization?",
        "options": [
            ("A", "Delivering chemotherapy into the tumor-feeding artery and blocking its blood supply"),
            ("B", "Draining bile through a catheter and keeping the bile duct open with a stent"),
            ("C", "Delivering chemotherapy into a vein and widening the tumor-feeding artery"),
            ("D", "Sampling tumor tissue and measuring pressure in the hepatic veins")
        ],
        "correct": "A"
    },
    {
        "section": "Interventional Radiology",
        "num": 71,
        "stem": "Why is portal vein embolization performed before some major liver operations?",
        "options": [
            ("A", "To promote growth of the liver portion that will remain after surgery"),
            ("B", "To obtain liver tissue through the internal jugular vein"),
            ("C", "To drain infected bile directly from the gallbladder"),
            ("D", "To shrink the liver portion that will remain after surgery")
        ],
        "correct": "A"
    },
    {
        "section": "Interventional Radiology",
        "num": 72,
        "stem": "What is the role of the balloon in kyphoplasty before bone cement is injected?",
        "options": [
            ("A", "To create a cavity and help restore vertebral height"),
            ("B", "To drain fluid from the spinal canal"),
            ("C", "To widen a narrowed spinal artery"),
            ("D", "To remove a herniated intervertebral disc")
        ],
        "correct": "A"
    },
    {
        "section": "Interventional Radiology",
        "num": 73,
        "stem": "What is the purpose of the tissue samples obtained during vacuum-assisted breast biopsy?",
        "options": [
            ("A", "To measure the size and boundaries of the lesion"),
            ("B", "To map the arterial supply and venous drainage of the lesion"),
            ("C", "To determine whether the lesion is benign or malignant"),
            ("D", "To assess the stiffness and compressibility of the lesion")
        ],
        "correct": "C"
    },
    {
        "section": "Interventional Radiology",
        "num": 74,
        "stem": "Which connection is created in a transjugular intrahepatic portosystemic shunt (TIPSS) to reduce portal hypertension?",
        "options": [
            ("A", "The portal vein to the inferior vena cava"),
            ("B", "The splenic vein to a renal vein"),
            ("C", "The hepatic artery to a hepatic vein"),
            ("D", "The portal vein to a hepatic vein")
        ],
        "correct": "D"
    },
    {
        "section": "Interventional Radiology",
        "num": 75,
        "stem": "Which statement correctly distinguishes fistuloplasty from thrombectomy in a blocked dialysis fistula?",
        "options": [
            ("A", "Fistuloplasty removes a clot, while thrombectomy creates a new fistula"),
            ("B", "Fistuloplasty inserts a dialysis catheter, while thrombectomy enlarges the artery"),
            ("C", "Fistuloplasty closes the fistula, while thrombectomy measures venous pressure"),
            ("D", "Fistuloplasty widens a narrowing, while thrombectomy removes a clot")
        ],
        "correct": "D"
    },
    {
        "section": "Interventional Radiology",
        "num": 76,
        "stem": "Which investigation best documents post-treatment venous status for a claim after catheter-directed thrombolysis of deep vein thrombosis?",
        "options": [
            ("A", "Pre-procedure Doppler establishing the original DVT"),
            ("B", "Baseline arterial Doppler documenting limb perfusion"),
            ("C", "Pretreatment contrast venography outlining the occluded veins"),
            ("D", "Post-procedure colour Doppler of the affected limb or part")
        ],
        "correct": "D"
    },
    {
        "section": "Interventional Radiology",
        "num": 77,
        "stem": "Which evidence set best documents the procedure and postoperative status for a claim after endovenous treatment of varicose veins?",
        "options": [
            ("A", "Post-procedure arterial angiogram, stent sticker, and angioplasty balloon invoice"),
            ("B", "Preoperative Doppler, the admission photograph, and the initial referral letter"),
            ("C", "Post-procedure venogram, thrombolytic-drug invoice, and thrombolysis-catheter invoice"),
            ("D", "Intraoperative photograph, postoperative colour Doppler, and postoperative clinical photograph")
        ],
        "correct": "D"
    },
    {
        "section": "Interventional Radiology",
        "num": 78,
        "stem": "Carotico-cavernous fistula embolization aims to block an abnormal connection between which structures?",
        "options": [
            ("A", "The portal vein and the inferior vena cava"),
            ("B", "The renal artery and the renal vein"),
            ("C", "The hepatic artery and the bile duct"),
            ("D", "The carotid artery and the cavernous sinus")
        ],
        "correct": "D"
    },
    {
        "section": "Interventional Radiology",
        "num": 79,
        "stem": "Which angioplasty-video finding demonstrates reopening of the treated artery after subclavian artery stenting?",
        "options": [
            ("A", "Visibility of embolization coils and complete arterial closure"),
            ("B", "Visibility of the stent and restoration of the arterial lumen"),
            ("C", "Visibility of a drainage catheter and resolution of a fluid collection"),
            ("D", "Visibility of an IVC filter and exclusion of leg-vein thrombosis")
        ],
        "correct": "B"
    },
    {
        "section": "Interventional Radiology",
        "num": 80,
        "stem": "How does cryoablation destroy tumor tissue?",
        "options": [
            ("A", "Freezing the tissue with extremely low temperatures"),
            ("B", "Infusing chemotherapy into its feeding artery"),
            ("C", "Blocking its arterial supply with embolic particles"),
            ("D", "Heating the tissue with microwave energy")
        ],
        "correct": "A"
    }
]


def seed_claim_80(reset: bool = False):
    run_advisory_lock_migration()
    session = SessionLocal()
    try:
        print("=" * 60)
        print("SEEDING CLAIM DEPARTMENT 80 QUESTIONS & ROSTER")
        print("=" * 60)

        # 1. Update / Provision Candidates in Roster (only clear attempts if reset=True)
        for cand in CLAIM_CANDIDATES:
            code = cand["code"]
            name = cand["name"]
            dept = cand["dept"]

            if reset:
                prior = session.query(Attempt).filter_by(employee_code=code).all()
                if prior:
                    p_ids = [p.id for p in prior]
                    session.query(Answer).filter(Answer.attempt_id.in_(p_ids)).delete(synchronize_session=False)
                    session.query(Violation).filter(Violation.attempt_id.in_(p_ids)).delete(synchronize_session=False)
                    session.query(Snapshot).filter(Snapshot.attempt_id.in_(p_ids)).delete(synchronize_session=False)
                    session.query(Event).filter(Event.attempt_id.in_(p_ids)).delete(synchronize_session=False)
                    session.query(Restart).filter(Restart.attempt_id.in_(p_ids)).delete(synchronize_session=False)
                    session.query(Attempt).filter(Attempt.id.in_(p_ids)).delete(synchronize_session=False)
                    session.commit()
                    print(f"  ✓ Purged prior attempts for {code} ({name})")
            else:
                print(f"  ℹ Preserving candidate attempt status for {code} ({name})")

            r = session.query(Roster).filter_by(employee_code=code).first()
            if not r:
                r = Roster(
                    employee_code=code,
                    full_name=name,
                    department="CLAIM",
                    role="CANDIDATE",
                    is_active=True
                )
                session.add(r)
                print(f"  + Enrolled Candidate: {code} | {name}")
            else:
                r.full_name = name
                r.department = "CLAIM"
                r.role = "CANDIDATE"
                r.is_active = True
                print(f"  ✓ Updated Candidate: {code} | {name}")
        session.commit()

        # 2. Find or create Claim Assessment
        claim_asm = session.query(Assessment).filter(Assessment.title.ilike("%CLAIM%")).first()
        if not claim_asm:
            claim_asm = Assessment(
                title="CS CREATIVE SOLUTIONS – CLAIM ASSESSMENT",
                duration_minutes=60,
                total_marks=80,
                marks_per_question=1,
                negative_marking=False,
                status="OPEN",
                settings={
                    "department": "CLAIM",
                    "short_code": "CLAIM",
                    "max_warnings": 5,
                    "look_away_limit_seconds": 4,
                    "no_face_limit_seconds": 3,
                    "window_blur_limit_seconds": 1,
                    "tab_switch_limit": 1
                }
            )
            session.add(claim_asm)
            session.commit()
            session.refresh(claim_asm)
        else:
            claim_asm.title = "CS CREATIVE SOLUTIONS – CLAIM ASSESSMENT"
            claim_asm.duration_minutes = 60
            claim_asm.total_marks = 80
            claim_asm.marks_per_question = 1
            claim_asm.negative_marking = False
            claim_asm.status = "OPEN"
            s = dict(claim_asm.settings or {})
            s["department"] = "CLAIM"
            s["short_code"] = "CLAIM"
            s["max_warnings"] = 5
            s["no_face_limit_seconds"] = 3
            s["look_away_limit_seconds"] = 4
            s["tab_switch_limit"] = 1
            claim_asm.settings = s
            session.commit()

        print(f"[*] Claim Assessment ID: {claim_asm.id}")

        # Check existing questions
        existing_q_count = session.query(Question).filter_by(assessment_id=claim_asm.id).count()
        if existing_q_count == len(CLAIM_QUESTIONS) and not reset:
            print(f"  ✓ Claim Assessment already has all {existing_q_count} questions configured. Skipping question re-insert.")
            return

        # 3. Wipe old questions from Claim Assessment if re-insert needed
        old_questions = session.query(Question).filter_by(assessment_id=claim_asm.id).all()
        if old_questions:
            old_q_ids = [q.id for q in old_questions]
            session.query(Option).filter(Option.question_id.in_(old_q_ids)).delete(synchronize_session=False)
            session.query(Question).filter_by(assessment_id=claim_asm.id).delete(synchronize_session=False)
            session.commit()
            print(f"  ✓ Removed {len(old_questions)} old questions from Claim assessment.")

        # Wipe old sections for this assessment
        session.query(Section).filter_by(assessment_id=claim_asm.id).delete(synchronize_session=False)
        session.commit()

        # 4. Create Sections
        section_names = [
            "Nephrology",
            "Paediatric Surgery",
            "Neurosurgery",
            "Polytrauma",
            "Pulmonology",
            "Interventional Radiology"
        ]
        sec_map = {}
        for idx, sname in enumerate(section_names, 1):
            sec = Section(
                assessment_id=claim_asm.id,
                name=sname,
                sort_order=idx
            )
            session.add(sec)
            session.commit()
            session.refresh(sec)
            sec_map[sname] = sec.id

        # 5. Insert all 80 questions with options and answer keys
        for q_data in CLAIM_QUESTIONS:
            s_id = sec_map[q_data["section"]]
            q = Question(
                assessment_id=claim_asm.id,
                section_id=s_id,
                source_number=q_data["num"],
                stem=q_data["stem"],
                marks=1,
                department="CLAIM"
            )
            session.add(q)
            session.commit()
            session.refresh(q)

            for label, opt_text in q_data["options"]:
                is_corr = (label == q_data["correct"])
                opt = Option(
                    question_id=q.id,
                    label=label,
                    text=opt_text,
                    is_correct=is_corr
                )
                session.add(opt)
            session.commit()

        print(f"  ✓ Successfully inserted all {len(CLAIM_QUESTIONS)} verified Claim questions.")
        print("=" * 60)
        print("[✓] CLAIM ASSESSMENT CONFIGURATION COMPLETE")
        print("=" * 60)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    seed_claim_80()
