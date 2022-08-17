#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Any, Optional

import whylogs as why
from whylogs.viz.extensions.reports.summary_drift import SummaryDriftReport
from whylogs.core.constraints import ConstraintsBuilder, MetricConstraint, Constraints

from airflow.exceptions import AirflowFailException
from airflow.models import BaseOperator


class WhylogsSummaryDriftOperator(BaseOperator):
    """
    This operator creates a whylogs' Summary Drift report from two existing whylogs profiles. 
    One of them is the reference profile, the "ground truth", and the other one is the target data, 
    meaning that this is what the report will compare it against.
    In order to have it working, users should also define what reader and writer they wish to use,
    leveraging the existing whylogs' API for this.

    :param target_profile_path: The target dataset profile path location.
    :type target_profile_path: str

    :param reference_profile_path: The reference dataset profile path location.
    :type reference_profile_path: str

    :param write_report_path: The location where you wish to store the HTML file for the Summary Drift
    Report
    :type write_report_path: str

    :param reader: The desired whylogs profile reader to choose from. Learn about the existing readers on [our docs](https://whylogs.readthedocs.io/en/latest/index.html). 
    Defaults to "local"
    :type reader: Optional, str

    :param writer: The desired whylogs profile writer to choose from. Learn about the existing writers on [our docs](https://whylogs.readthedocs.io/en/latest/index.html). 
    Defaults to "local".
    :type writer:  Optional, str

    """
    def __init__(
            self,
            *,
            target_profile_path: str,
            reference_profile_path: str,
            write_report_path: str,
            reader: Optional[str] = "local",
            writer: Optional[str] = "local",
            **kwargs
    ):
        super().__init__(**kwargs)
        self.target_profile_path = target_profile_path
        self.reference_profile_path = reference_profile_path
        self.write_report_path = write_report_path
        self.reader = reader
        self.writer = writer

    def execute(self, **kwargs) -> Any:
        reference_view = why.reader(self.reader).read(path=self.reference_profile_path).view()
        target_view = why.reader(self.reader).read(path=self.target_profile_path).view()

        report = SummaryDriftReport(ref_view=reference_view, target_view=target_view)
        report.writer(self.writer).write(dest=self.write_report_path)
        self.log.info(f"Whylogs' summary drift report successfully written to {self.writer}")


class WhylogsConstraintsOperator(BaseOperator):
    """
    Creates a whylogs' Constraints report from a `Constraints` object or by using our pre-defined contraint factories,
    as the example below shows. 
    Currently our API requires the user to have a profiled DataFrame in place to be able to use it, so you will have to point
    to a location where a profiled dataset exists. Then the operator will run a constraint suite that will check which conditions have
    passed or failed. Users will also be able to leverage this to stop executions in case some criteria is not met.
    
    :param profile_path: The dataset profile path location, in case you want to use a single built-in constraint. Defaults to None.
    :type profile_path: Optional, str

    :param reader: The desired whylogs profile reader to choose from. Learn about the existing readers on [our docs](https://whylogs.readthedocs.io/en/latest/index.html). 
    Defaults to None.
    :type reader: Optional, str

    constraint
    constraints  
    break_pipeline

    :param constraint: A MetricConstraints object, that can be used by leveraging the existing constraint factories on whylogs, 
    as the example below shows. Defaults to None.
    :type constraint: `:class:MetricConstraint`, Optional

    :param constraints: A Constraints object, that will have a user-defined constraints suite, as the second example below shows.
    Defaults to None.
    :type constraints: `:class:Constraint`, Optional

    :param break_pipeline: Decide if you wish to raise an Airflow Exception and stop the existing DAG execution. Defaults to False
    :type break_pipeline: bool 


    .. code-block:: python
        
        from whylogs.core.constraints.factories import greater_than_number

        TASK_ID = "column_1_check"
        PROFILE_PATH = "s3://some/prefix/to/a/profile.bin"

        with DAG(dag_id='constraints_example', start_date=datetime.now()) as dag: 

            op = WhylogsConstraintsOperator(
                task_id=TASK_ID,
                profile_path=PROFILE_PATH,
                reader="s3",
                constraint=greater_than_number(number=0.0, column="column_1")
            )

            op 

    This allows for a higher granularity in terms of quickly identifying which tasks have failed, and also can
    make the DAG more lenient towards breaking with some core checks and raising a warning with others. If instead you wish to
    run all checks in a single task, the best thing is to inject a `:class:Constraints` object. The following example demonstrates how 
    to do it:

    .. code-block:: python
        
        from whylogs.core.constraints.factories import smaller_than_number, mean_between_range, null_percentage_below_number

        TASK_ID = "column_1_check"
        PROFILE_PATH = "s3://some/prefix/to/a/profile.bin"

        def build_constraints():
            profile_view = why.reader("s3").read(path=PROFILE_PATH)

            builder = ConstraintsBuilder(dataset_profile_view=profile_view)
            builder.add_constraint(smaller_than_number(column_name="bp", number=20.0))
            builder.add_constraint(mean_between_range(column_name="s3", lower=-1.5, upper=1.5))
            builder.add_constraint(null_percentage_below_number(column_name="sex", number=0.0))

            constraints = builder.build()
            return constraints

        with DAG(dag_id='constraints_example', start_date=datetime.now()) as dag: 

            op = WhylogsConstraintsOperator(
                task_id=TASK_ID,
                profile_path=PROFILE_PATH,
                reader="s3",
                constraints=build_constraints()
            )

            op 

    If you want to learn more about running constraint checks with whylogs, please check out our [docs and examples](https://whylogs.readthedocs.io/)
    """
    def __init__(
            self,
            *,
            profile_path: Optional[str] = None,
            reader: Optional[str] = None,
            constraint: Optional[MetricConstraint] = None,
            constraints: Optional[Constraints] = None,
            break_pipeline: Optional[bool] = False,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.profile_path = profile_path
        self.reader = reader
        self.constraint = constraint
        self.constraints = constraints
        self.break_pipeline = break_pipeline

    def _get_or_create_constraints(self):
        if self.constraints is None:
            profile_view = why.reader(self.reader).read(path=self.profile_path).view()
            builder = ConstraintsBuilder(profile_view)
            builder.add_constraint(self.constraint)
            constraints = builder.build()
            return constraints
        else:
            return self.constraints

    def execute(self, **kwargs):
        constraints = self._get_or_create_constraints()
        result: bool = constraints.validate()
        if result is False and self.break_pipeline:
            self.log.error(constraints.report())
            raise AirflowFailException("Constraints didn't meet the criteria")
        elif result is False and not self.break_pipeline:
            self.log.warning(constraints.report())
        else:
            self.log.info(constraints.report())
        return result
