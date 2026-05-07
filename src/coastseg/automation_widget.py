
import os
import logging
import ipywidgets as widgets
from IPython.display import display
from coastseg import tide_correction
import prepare_portal_data
import generate_tides_for_session
import geopandas as gpd
from ipyfilechooser import FileChooser

logger = logging.getLogger(__name__)

class AutomationWidget:
    def __init__(self, parent_ui):
        self.parent_ui = parent_ui
        self.output_view = widgets.Output(layout={'border': '1px solid gray', 'height': '250px', 'overflow': 'auto'})
        self.progress_bar = widgets.FloatProgress(value=0.0, min=0.0, max=1.0, description='Progress:', layout={'width': '100%'})
        self.status_label = widgets.Label(value='Ready to start automation...')
        
        # Session Selection via FileChooser
        sessions_dir = os.path.join(os.getcwd(), 'sessions')
        if not os.path.exists(sessions_dir):
            sessions_dir = os.getcwd()
            
        self.file_chooser = FileChooser(
            sessions_dir,
            title='<b>Select Target Session Folder:</b>',
            show_only_dirs=True,
            select_default=True,
            layout={'width': '100%'}
        )
        
        # Individual Step Buttons
        self.btn_step1 = widgets.Button(description='1. Predict Tides & Slopes', layout={'width': '250px'})
        self.btn_step2 = widgets.Button(description='2. Run Tidal Correction', layout={'width': '250px'})
        self.btn_step3 = widgets.Button(description='3. Export Local Portal Data', layout={'width': '250px'})
        self.btn_step4 = widgets.Button(description='4. Run Global Aggregation', layout={'width': '250px'})
        
        # Full Automation Button
        self.run_all_button = widgets.Button(
            description='Run Full Automation & Export',
            button_style='success',
            tooltip='Run all steps in sequence',
            icon='play',
            layout={'width': '508px', 'margin': '10px 0px 0px 0px'}
        )
        
        # Set callbacks
        self.btn_step1.on_click(lambda b: self.run_step(1))
        self.btn_step2.on_click(lambda b: self.run_step(2))
        self.btn_step3.on_click(lambda b: self.run_step(3))
        self.btn_step4.on_click(lambda b: self.run_step(4))
        self.run_all_button.on_click(self.on_run_all_clicked)
        
        # Try to auto-select path from parent UI
        parent_path = self.get_parent_session_path()
        if parent_path and os.path.exists(parent_path):
            self.file_chooser.reset(path=os.path.dirname(parent_path), filename=os.path.basename(parent_path))
        
        # Organize in Rows
        row1 = widgets.HBox([self.btn_step1, self.btn_step2])
        row2 = widgets.HBox([self.btn_step3, self.btn_step4])
        
        self.container = widgets.VBox([
            widgets.HTML("<h2>Automation & Portal Export</h2>"),
            widgets.HTML("<p>Use the folder picker to select a session, then run automation steps.</p>"),
            self.file_chooser,
            self.status_label,
            self.progress_bar,
            widgets.VBox([row1, row2, self.run_all_button]),
            widgets.HTML("<br><b>Console Output:</b>"),
            self.output_view
        ])

    def get_parent_session_path(self):
        """Attempts to get session path from the main CoastSeg UI components."""
        if hasattr(self.parent_ui, 'coastseg_map'):
            return self.parent_ui.coastseg_map.get_session_path()
        elif hasattr(self.parent_ui, 'model_session_directory') and self.parent_ui.model_session_directory:
            return self.parent_ui.model_session_directory
        return None

    def get_session_path(self):
        """Returns the currently selected session path from FileChooser."""
        return self.file_chooser.selected

    def set_buttons_state(self, disabled=True):
        self.btn_step1.disabled = disabled
        self.btn_step2.disabled = disabled
        self.btn_step3.disabled = disabled
        self.btn_step4.disabled = disabled
        self.run_all_button.disabled = disabled
        self.file_chooser.disabled = disabled

    def run_step(self, step_num):
        self.output_view.clear_output()
        self.set_buttons_state(True)
        
        with self.output_view:
            try:
                session_path = self.get_session_path()
                if not session_path or not os.path.exists(session_path):
                    print("❌ Error: No session folder selected or path does not exist.")
                    return

                if step_num == 1:
                    self.execute_step1(session_path)
                elif step_num == 2:
                    self.execute_step2(session_path)
                elif step_num == 3:
                    self.execute_step3(session_path)
                elif step_num == 4:
                    self.execute_step4(session_path)
                
            except Exception as e:
                self.status_label.value = f"❌ Error in Step {step_num}. Check console."
                print(f"\n❌ Error: {str(e)}")
                logger.exception(e)
            finally:
                self.set_buttons_state(False)

    def execute_step1(self, session_path):
        self.status_label.value = "Executing Step 1: Predicting Tides & Estimating Slopes..."
        print(f"🚀 [Step 1] Processing: {os.path.basename(session_path)}")
        generate_tides_for_session.prepare_tides_and_slopes(session_path)
        self.progress_bar.value = 0.25
        print("✅ [Step 1] Completed.")

    def execute_step2(self, session_path):
        self.status_label.value = "Executing Step 2: Running Tidal Correction..."
        session_name = os.path.basename(session_path.rstrip('/'))
        print(f"🚀 [Step 2] Processing: {session_name}")
        
        config_gdf_path = os.path.join(session_path, 'config_gdf.geojson')
        if not os.path.exists(config_gdf_path):
            raise FileNotFoundError(f"config_gdf.geojson not found in {session_path}")

        config_gdf = gpd.read_file(config_gdf_path)
        roi_ids = config_gdf[config_gdf['type'] == 'roi']['id'].unique().tolist()
        
        tides_file = os.path.join(session_path, "predicted_tides.csv")
        slopes_file = os.path.join(session_path, "estimated_beach_slopes.csv")
        
        tide_correction.correct_all_tides(
            roi_ids=roi_ids,
            session_name=session_name,
            beach_slope=slopes_file,
            tides_file=tides_file,
            reference_elevation=0
        )
        self.progress_bar.value = 0.50
        print("✅ [Step 2] Completed.")

    def execute_step3(self, session_path):
        self.status_label.value = "Executing Step 3: Exporting Local Portal Data..."
        print(f"🚀 [Step 3] Processing: {os.path.basename(session_path)}")
        prepare_portal_data.prepare_portal_data(session_path)
        self.progress_bar.value = 0.75
        print("✅ [Step 3] Completed.")

    def execute_step4(self, session_path):
        self.status_label.value = "Executing Step 4: Running Global Aggregation..."
        # Project root should be 2 levels up from a session folder (sessions/session_name)
        project_root = os.path.dirname(os.path.dirname(session_path))
        # If the user selected a folder outside 'sessions', fallback to current working directory
        if os.path.basename(os.path.dirname(session_path)) != 'sessions':
            project_root = os.getcwd()
            
        sessions_root = os.path.join(project_root, "sessions")
        output_base = os.path.join(project_root, "global_portal_output")
        
        print(f"🚀 [Step 4] Aggregating all sessions from: {sessions_root}")
        prepare_portal_data.prepare_global_portal_data(sessions_root, output_base)
        self.progress_bar.value = 1.0
        print(f"✅ [Step 4] Global aggregation completed at: {output_base}")

    def on_run_all_clicked(self, b):
        self.output_view.clear_output()
        self.set_buttons_state(True)
        self.progress_bar.value = 0
        
        with self.output_view:
            try:
                session_path = self.get_session_path()
                if not session_path or not os.path.exists(session_path):
                    print("❌ Error: No session folder selected.")
                    return

                self.execute_step1(session_path)
                self.execute_step2(session_path)
                self.execute_step3(session_path)
                self.execute_step4(session_path)

                self.status_label.value = "🏁 All processes finished successfully!"
                print("\n🎉 Done! Full automation completed.")

            except Exception as e:
                self.status_label.value = "❌ Automation failed. Check console."
                print(f"\n❌ Error: {str(e)}")
                logger.exception(e)
            finally:
                self.set_buttons_state(False)
