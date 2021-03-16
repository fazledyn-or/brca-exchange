import logging
import os
import tarfile
import luigi
from luigi.util import requires

from workflow import pipeline_utils
from workflow.pipeline_common import DefaultPipelineTask

###############################################
#                  gnomAD                     #
###############################################

gnomAD_method_dir = os.path.abspath('../gnomad')

logger = logging.getLogger('gnomAD')


class GnomADTask(DefaultPipelineTask):
    def __init__(self, *args, **kwargs):
        super(GnomADTask, self).__init__(*args, **kwargs)


class DownloadGnomADData(GnomADTask):
    gnomAD_v2_static_data_url = luigi.Parameter(default='https://brcaexchange.org/backend/downloads/gnomAD_v2_hg19_10_02_2020.tsv',
                                            description='URL to download static gnomAD v2 data from')
    gnomAD_v3_static_data_url = luigi.Parameter(default='https://brcaexchange.org/backend/downloads/gnomAD_v3_GRCh38_03_10_2021.tsv',
                                            description='URL to download static gnomAD v3 data from')

    def output(self):
        return { "v2": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomAD_v2_hg19_10_02_2020.tsv"),
                 "v3": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomAD_v3_GRCh38_03_10_2021.tsv")}

    def run(self):
        data = pipeline_utils.urlopen_with_retry(self.gnomAD_v2_static_data_url).read()
        with open(self.output()["v2"].path, "wb") as f:
            f.write(data)

        data = pipeline_utils.urlopen_with_retry(self.gnomAD_v3_static_data_url).read()
        with open(self.output()["v3"].path, "wb") as f:
            f.write(data)


@requires(DownloadGnomADData)
class ConvertGnomADToVCF(GnomADTask):
    def output(self):
        return { "v2": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomADv2.hg19.vcf"),
                 "v3": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomADv3.hg38.vcf")}

    def run(self):
        os.chdir(gnomAD_method_dir)

        for file in self.input().keys():
            args = ["python", "gnomad_to_vcf.py", "-i", self.input()[file], "-o",
                    self.output()[file].path, "-a", "gnomADAnnotation",
                    "-l", self.artifacts_dir + "/gnomADv2_error_variants.log",
                    "-s", "gnomAD"]

            pipeline_utils.run_process(args)
            pipeline_utils.check_file_for_contents(self.output()[file].path)


@requires(ConvertGnomADToVCF)
class CrossmapGnomADV2Data(GnomADTask):
    def output(self):
        return luigi.LocalTarget(os.path.join(self.gnomad_file_dir, "gnomADv2.hg38.vcf"))

    def run(self):
        brca_resources_dir = self.cfg.resources_dir

        args = ["CrossMap.py", "vcf", brca_resources_dir + "/hg19ToHg38.over.chain.gz",
                self.input().path, brca_resources_dir + "/hg38.fa",
                self.output().path]

        pipeline_utils.run_process(args)
        pipeline_utils.check_file_for_contents(self.output().path)


@requires(CrossmapGnomADV2Data)
class SortGnomADData(GnomADTask):
    def output(self):
        return { "v2": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomADv2.sorted.hg38.vcf"),
                 "v3": luigi.LocalTarget(f"{self.gnomad_file_dir}/gnomADv3.sorted.hg38.vcf")}

    def run(self):
        for key in self.output().keys():
            args = ["vcf-sort", f"{self.gnomad_file_dir}/gnomAD{key}.hg38.vcf"]
            pipeline_utils.run_process(args, redirect_stdout_path=self.output()[key].path)
            pipeline_utils.check_file_for_contents(self.output()[key].path)
