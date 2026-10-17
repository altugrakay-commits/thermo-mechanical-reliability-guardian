# agent.py
import os
import gitlab
from parser import DesignParser
from physics_engine import ThermoMechanicalEngine

def main():
    # 1. Parse the design file (Assuming a config file in the repo)
    parser = DesignParser('design_config.json')
    data = parser.parse()
    
    # 2. Run physics engine
    engine = ThermoMechanicalEngine({})
    results = engine.run_full_analysis(data)
    
    # 3. Post comment to MR using GitLab API
    GITLAB_TOKEN = os.environ.get('GITLAB_TOKEN')
    CI_PROJECT_ID = os.environ.get('CI_PROJECT_ID')
    CI_MERGE_REQUEST_IID = os.environ.get('CI_MERGE_REQUEST_IID')
    
    if GITLAB_TOKEN and CI_PROJECT_ID and CI_MERGE_REQUEST_IID:
        gl = gitlab.Gitlab('https://gitlab.com', private_token=GITLAB_TOKEN)
        project = gl.projects.get(CI_PROJECT_ID)
        mr = project.mergerequests.get(CI_MERGE_REQUEST_IID)
        
        comment = f"### 🛡️ Thermo-Mechanical Reliability Report\n\n"
        comment += f"- **Darveaux Cycles:** {results['darveaux_cycles']}\n"
        comment += f"- **Norris-Landzberg Cycles:** {results['norris_landzberg_cycles']}\n"
        comment += f"- **Status:** {results['status']}\n"
        comment += f"- **Delta T:** {results['delta_T']}K\n"
        
        mr.notes.create({'body': comment})
        print("Comment posted successfully!")
    else:
        print("Running locally. Results:")
        print(results)

if __name__ == "__main__":
    main()