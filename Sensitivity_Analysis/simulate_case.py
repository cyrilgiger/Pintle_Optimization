import sys
import logging
from pathlib import Path
import pandas as pd
from Functions.run_fun import prepare_case, run_case

logger = logging.getLogger(__name__)

def simulate_case(case_id: int):
    str_case_id = f"case_{case_id:04d}"
    base_dir = Path(__file__).resolve().parent / "cases"  # directory such that: base_dir/case_0000, case_0001, ...
    logger.info("Starting case %s", str_case_id)
    df_cases = pd.read_csv("case_data.csv")
    df_case = df_cases.loc[df_cases["case_id"] == str_case_id].iloc[0].to_dict()

    prepare_case(str_case_id, df_case, base_dir)
    logger.info("Prepared: %s", str_case_id)

    run_case(str_case_id, base_dir)
    logger.info("Ran: %s", str_case_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s %(name)s.%(funcName)s: %(message)s",
    )
    # sys.argv[0] is the script name, sys.argv[1] is the first argument
    case_id = int(sys.argv[1])
    # case_id = 10
    simulate_case(case_id)