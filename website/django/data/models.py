from django.db import models
from django.contrib.postgres.fields import JSONField

class DataRelease(models.Model):
    schema = models.TextField()
    archive = models.TextField()
    date = models.DateTimeField()
    notes = models.TextField()
    sources = models.TextField()
    md5sum = models.TextField()
    created = models.DateTimeField(auto_now_add=True, null=True)
    name = models.PositiveIntegerField()

    class Meta:
        db_table = "data_release"
        ordering = ['date']

class ChangeType(models.Model):
    name = models.TextField()

class LegacyJSONField(JSONField):
    def db_type(self, connection):
        return 'json'

class VariantDiff(models.Model):
    variant = models.OneToOneField('Variant', primary_key=True)
    # Postgres-specific JSON field. If migrating away from postgres, use TextField instead
    # provides JSON validation
    diff = LegacyJSONField()

class ReportDiff(models.Model):
    report = models.OneToOneField('Report', primary_key=True)
    # Postgres-specific JSON field. If migrating away from postgres, use TextField instead
    # provides JSON validation
    report_diff = LegacyJSONField()

class VariantManager(models.Manager):
    def create_variant(self, row):
        return self.create(**row)

class Variant(models.Model):
    # These are some extra derived columns that help with filtering
    Variant_in_ENIGMA = models.BooleanField(default=False)
    Variant_in_ClinVar = models.BooleanField(default=False)
    Variant_in_1000_Genomes = models.BooleanField(default=False)
    Variant_in_ExAC = models.BooleanField(default=False)
    Variant_in_LOVD = models.BooleanField(default=False)
    Variant_in_BIC = models.BooleanField(default=False)
    Variant_in_ESP = models.BooleanField(default=False)
    Variant_in_exLOVD = models.BooleanField(default=False)

    Source = models.TextField()
    URL_ENIGMA = models.TextField()
    Condition_ID_type_ENIGMA = models.TextField()
    Condition_ID_value_ENIGMA = models.TextField()
    Condition_category_ENIGMA = models.TextField()
    Clinical_significance_ENIGMA = models.TextField()
    Date_last_evaluated_ENIGMA = models.TextField()
    Assertion_method_ENIGMA = models.TextField()
    Assertion_method_citation_ENIGMA = models.TextField()
    Clinical_significance_citations_ENIGMA = models.TextField()
    Comment_on_clinical_significance_ENIGMA = models.TextField()
    Collection_method_ENIGMA = models.TextField()
    Allele_origin_ENIGMA = models.TextField()
    ClinVarAccession_ENIGMA = models.TextField()
    Clinical_Significance_ClinVar = models.TextField()
    Date_Last_Updated_ClinVar = models.TextField()
    Submitter_ClinVar = models.TextField()
    SCV_ClinVar = models.TextField()
    Allele_Origin_ClinVar = models.TextField()
    Method_ClinVar = models.TextField()
    Functional_analysis_result_LOVD = models.TextField()
    Functional_analysis_technique_LOVD = models.TextField()
    Variant_frequency_LOVD = models.TextField()
    Variant_haplotype_LOVD = models.TextField()
    HGVS_cDNA_LOVD = models.TextField()
    HGVS_protein_LOVD = models.TextField()
    Individuals_LOVD = models.TextField()
    Variant_effect_LOVD = models.TextField()
    Genetic_origin_LOVD = models.TextField()
    RNA_LOVD = models.TextField()
    Submitters_LOVD = models.TextField()
    Created_date_LOVD = models.TextField(default="-")
    Edited_date_LOVD = models.TextField(default="-")
    DBID_LOVD = models.TextField(default="-")
    Minor_allele_frequency_percent_ESP = models.TextField()
    EA_Allele_Frequency_ESP = models.TextField(default="-")
    AA_Allele_Frequency_ESP = models.TextField(default="-")
    Allele_Frequency_ESP = models.TextField(default="-")
    EUR_Allele_frequency_1000_Genomes = models.TextField()
    AFR_Allele_frequency_1000_Genomes = models.TextField()
    AMR_Allele_frequency_1000_Genomes = models.TextField()
    EAS_Allele_frequency_1000_Genomes = models.TextField()
    Allele_frequency_1000_Genomes = models.TextField()
    SAS_Allele_frequency_1000_Genomes = models.TextField()
    Allele_frequency_ExAC = models.TextField()
    Allele_count_AFR_ExAC = models.TextField(default="-")
    Allele_number_AFR_ExAC = models.TextField(default="-")
    Allele_frequency_AFR_ExAC = models.TextField(default="-")
    Homozygous_count_AFR_ExAC = models.TextField(default="-")
    Allele_count_AMR_ExAC = models.TextField(default="-")
    Allele_number_AMR_ExAC = models.TextField(default="-")
    Allele_frequency_AMR_ExAC = models.TextField(default="-")
    Homozygous_count_AMR_ExAC = models.TextField(default="-")
    Allele_count_EAS_ExAC = models.TextField(default="-")
    Allele_number_EAS_ExAC = models.TextField(default="-")
    Allele_frequency_EAS_ExAC = models.TextField(default="-")
    Homozygous_count_EAS_ExAC = models.TextField(default="-")
    Allele_count_FIN_ExAC = models.TextField(default="-")
    Allele_number_FIN_ExAC = models.TextField(default="-")
    Allele_frequency_FIN_ExAC = models.TextField(default="-")
    Homozygous_count_FIN_ExAC = models.TextField(default="-")
    Allele_count_NFE_ExAC = models.TextField(default="-")
    Allele_number_NFE_ExAC = models.TextField(default="-")
    Allele_frequency_NFE_ExAC = models.TextField(default="-")
    Homozygous_count_NFE_ExAC = models.TextField(default="-")
    Allele_count_OTH_ExAC = models.TextField(default="-")
    Allele_number_OTH_ExAC = models.TextField(default="-")
    Allele_frequency_OTH_ExAC = models.TextField(default="-")
    Homozygous_count_OTH_ExAC = models.TextField(default="-")
    Allele_count_SAS_ExAC = models.TextField(default="-")
    Allele_number_SAS_ExAC = models.TextField(default="-")
    Allele_frequency_SAS_ExAC = models.TextField(default="-")
    Homozygous_count_SAS_ExAC = models.TextField(default="-")
    Patient_nationality_BIC = models.TextField()
    Clinical_importance_BIC = models.TextField()
    Clinical_classification_BIC = models.TextField()
    Literature_citation_BIC = models.TextField()
    Number_of_family_member_carrying_mutation_BIC = models.TextField()
    Germline_or_Somatic_BIC = models.TextField()
    Ethnicity_BIC = models.TextField()
    Mutation_type_BIC = models.TextField()
    IARC_class_exLOVD = models.TextField()
    Sum_family_LR_exLOVD = models.TextField()
    Combined_prior_probablility_exLOVD = models.TextField()
    Literature_source_exLOVD = models.TextField()
    Co_occurrence_LR_exLOVD = models.TextField()
    Posterior_probability_exLOVD = models.TextField()
    Missense_analysis_prior_probability_exLOVD = models.TextField()
    Segregation_LR_exLOVD = models.TextField()
    Gene_Symbol = models.TextField()
    Reference_Sequence = models.TextField()
    HGVS_cDNA = models.TextField()
    BIC_Nomenclature = models.TextField()
    HGVS_Protein = models.TextField()
    HGVS_RNA = models.TextField()
    Protein_Change = models.TextField()
    Allele_Frequency = models.TextField()
    Max_Allele_Frequency = models.TextField()
    Genomic_Coordinate_hg38 = models.TextField()
    Hg38_Start = models.BigIntegerField(default=1)
    Hg38_End = models.BigIntegerField(default=1)
    Hg37_Start = models.BigIntegerField(default=1)
    Hg37_End = models.BigIntegerField(default=1)
    Hg36_Start = models.BigIntegerField(default=1)
    Hg36_End = models.BigIntegerField(default=1)
    Genomic_Coordinate_hg37 = models.TextField()
    Genomic_Coordinate_hg36 = models.TextField()
    Source_URL = models.TextField()
    Discordant = models.TextField()
    Synonyms = models.TextField()
    Pathogenicity_expert = models.TextField()
    Pathogenicity_all = models.TextField()
    Chr = models.TextField()
    Pos = models.TextField()
    Ref = models.TextField()
    Alt = models.TextField()
    Polyphen_Prediction = models.TextField()
    Polyphen_Score = models.TextField()
    Sift_Score = models.TextField()
    Sift_Prediction = models.TextField()
    BX_ID_ENIGMA = models.TextField(default='')
    BX_ID_LOVD = models.TextField(default='')
    BX_ID_ESP = models.TextField(default='')
    BX_ID_BIC = models.TextField(default='')
    BX_ID_ClinVar = models.TextField(default='')
    BX_ID_1000_Genomes = models.TextField(default='')
    BX_ID_ExAC = models.TextField(default='')
    BX_ID_exLOVD = models.TextField(default='')

    # Data Versioning
    Data_Release = models.ForeignKey(DataRelease)
    Change_Type = models.ForeignKey(ChangeType)

    objects = VariantManager()

    class Meta:
        db_table = 'variant'


class ReportManager(models.Manager):
    def create_report(self, row):
        return self.create(**row)


class Report(models.Model):
    Variant = models.ForeignKey('Variant')
    Source = models.TextField()
    Gene_symbol_ENIGMA = models.TextField()
    Genomic_Coordinate = models.TextField()
    Chr = models.TextField()
    Pos = models.TextField()
    Ref = models.TextField()
    Alt = models.TextField()
    Reference_sequence_ENIGMA = models.TextField()
    HGVS_cDNA_ENIGMA = models.TextField()
    BIC_Nomenclature_ENIGMA = models.TextField()
    Abbrev_AA_change_ENIGMA = models.TextField()
    URL_ENIGMA = models.TextField()
    Condition_ID_type_ENIGMA = models.TextField()
    Condition_ID_value_ENIGMA = models.TextField()
    Condition_category_ENIGMA = models.TextField()
    Clinical_significance_ENIGMA = models.TextField()
    Date_last_evaluated_ENIGMA = models.TextField()
    Assertion_method_ENIGMA = models.TextField()
    Assertion_method_citation_ENIGMA = models.TextField()
    Clinical_significance_citations_ENIGMA = models.TextField()
    Comment_on_clinical_significance_ENIGMA = models.TextField()
    Collection_method_ENIGMA = models.TextField()
    Allele_origin_ENIGMA = models.TextField()
    ClinVarAccession_ENIGMA = models.TextField()
    HGVS_protein_ENIGMA = models.TextField()
    BX_ID_ENIGMA = models.TextField()
    Clinical_Significance_ClinVar = models.TextField()
    Date_Last_Updated_ClinVar = models.TextField()
    BX_ID_ClinVar = models.TextField()
    HGVS_ClinVar = models.TextField()
    Submitter_ClinVar = models.TextField()
    Protein_ClinVar = models.TextField()
    SCV_ClinVar = models.TextField()
    Allele_Origin_ClinVar = models.TextField()
    Method_ClinVar = models.TextField()
    Description_ClinVar = models.TextField(default="-")
    Summary_Evidence_ClinVar = models.TextField(default="-")
    Review_Status_ClinVar = models.TextField(default="-")
    BX_ID_LOVD = models.TextField()
    Variant_frequency_LOVD = models.TextField()
    HGVS_cDNA_LOVD = models.TextField()
    HGVS_protein_LOVD = models.TextField()
    Individuals_LOVD = models.TextField()
    Variant_effect_LOVD = models.TextField()
    Genetic_origin_LOVD = models.TextField()
    RNA_LOVD = models.TextField()
    Submitters_LOVD = models.TextField()
    Created_date_LOVD = models.TextField(default="-")
    Edited_date_LOVD = models.TextField(default="-")
    DBID_LOVD = models.TextField(default="-")
    BX_ID_ESP = models.TextField()
    Minor_allele_frequency_percent_ESP = models.TextField()
    EA_Allele_Frequency_ESP = models.TextField(default="-")
    AA_Allele_Frequency_ESP = models.TextField(default="-")
    Allele_Frequency_ESP = models.TextField(default="-")
    polyPhen2_result_ESP = models.TextField()
    EUR_Allele_frequency_1000_Genomes = models.TextField()
    AFR_Allele_frequency_1000_Genomes = models.TextField()
    AMR_Allele_frequency_1000_Genomes = models.TextField()
    EAS_Allele_frequency_1000_Genomes = models.TextField()
    BX_ID_1000_Genomes = models.TextField()
    Allele_frequency_1000_Genomes = models.TextField()
    SAS_Allele_frequency_1000_Genomes = models.TextField()
    Allele_frequency_ExAC = models.TextField()
    Allele_count_AFR_ExAC = models.TextField(default="-")
    Allele_number_AFR_ExAC = models.TextField(default="-")
    Allele_frequency_AFR_ExAC = models.TextField(default="-")
    Homozygous_count_AFR_ExAC = models.TextField(default="-")
    Allele_count_AMR_ExAC = models.TextField(default="-")
    Allele_number_AMR_ExAC = models.TextField(default="-")
    Allele_frequency_AMR_ExAC = models.TextField(default="-")
    Homozygous_count_AMR_ExAC = models.TextField(default="-")
    Allele_count_EAS_ExAC = models.TextField(default="-")
    Allele_number_EAS_ExAC = models.TextField(default="-")
    Allele_frequency_EAS_ExAC = models.TextField(default="-")
    Homozygous_count_EAS_ExAC = models.TextField(default="-")
    Allele_count_FIN_ExAC = models.TextField(default="-")
    Allele_number_FIN_ExAC = models.TextField(default="-")
    Allele_frequency_FIN_ExAC = models.TextField(default="-")
    Homozygous_count_FIN_ExAC = models.TextField(default="-")
    Allele_count_NFE_ExAC = models.TextField(default="-")
    Allele_number_NFE_ExAC = models.TextField(default="-")
    Allele_frequency_NFE_ExAC = models.TextField(default="-")
    Homozygous_count_NFE_ExAC = models.TextField(default="-")
    Allele_count_OTH_ExAC = models.TextField(default="-")
    Allele_number_OTH_ExAC = models.TextField(default="-")
    Allele_frequency_OTH_ExAC = models.TextField(default="-")
    Homozygous_count_OTH_ExAC = models.TextField(default="-")
    Allele_count_SAS_ExAC = models.TextField(default="-")
    Allele_number_SAS_ExAC = models.TextField(default="-")
    Allele_frequency_SAS_ExAC = models.TextField(default="-")
    Homozygous_count_SAS_ExAC = models.TextField(default="-")
    BX_ID_ExAC = models.TextField()
    BX_ID_BIC = models.TextField()
    Patient_nationality_BIC = models.TextField()
    Clinical_importance_BIC = models.TextField()
    Clinical_classification_BIC = models.TextField()
    BIC_Designation_BIC = models.TextField()
    Literature_citation_BIC = models.TextField()
    Number_of_family_member_carrying_mutation_BIC = models.TextField()
    Germline_or_Somatic_BIC = models.TextField()
    Ethnicity_BIC = models.TextField()
    Mutation_type_BIC = models.TextField()
    IARC_class_exLOVD = models.TextField()
    BIC_Nomenclature_exLOVD = models.TextField()
    Sum_family_LR_exLOVD = models.TextField()
    Combined_prior_probablility_exLOVD = models.TextField()
    BX_ID_exLOVD = models.TextField()
    HGVS_cDNA_exLOVD = models.TextField()
    Literature_source_exLOVD = models.TextField()
    Co_occurrence_LR_exLOVD = models.TextField()
    Posterior_probability_exLOVD = models.TextField()
    Missense_analysis_prior_probability_exLOVD = models.TextField()
    Segregation_LR_exLOVD = models.TextField()
    HGVS_protein_exLOVD = models.TextField()

    Data_Release = models.ForeignKey(DataRelease)
    Change_Type = models.ForeignKey(ChangeType)

    objects = ReportManager()

    class Meta:
        db_table = 'report'


# materialized view containing only the most current version of each variant
class CurrentVariant(models.Model):
    # These are some extra derived columns that help with filtering
    Variant_in_ENIGMA = models.BooleanField(default=False)
    Variant_in_ClinVar = models.BooleanField(default=False)
    Variant_in_1000_Genomes = models.BooleanField(default=False)
    Variant_in_ExAC = models.BooleanField(default=False)
    Variant_in_LOVD = models.BooleanField(default=False)
    Variant_in_BIC = models.BooleanField(default=False)
    Variant_in_ESP = models.BooleanField(default=False)
    Variant_in_exLOVD = models.BooleanField(default=False)

    Source = models.TextField()
    URL_ENIGMA = models.TextField()
    Condition_ID_type_ENIGMA = models.TextField()
    Condition_ID_value_ENIGMA = models.TextField()
    Condition_category_ENIGMA = models.TextField()
    Clinical_significance_ENIGMA = models.TextField()
    Date_last_evaluated_ENIGMA = models.TextField()
    Assertion_method_ENIGMA = models.TextField()
    Assertion_method_citation_ENIGMA = models.TextField()
    Clinical_significance_citations_ENIGMA = models.TextField()
    Comment_on_clinical_significance_ENIGMA = models.TextField()
    Collection_method_ENIGMA = models.TextField()
    Allele_origin_ENIGMA = models.TextField()
    ClinVarAccession_ENIGMA = models.TextField()
    Clinical_Significance_ClinVar = models.TextField()
    Date_Last_Updated_ClinVar = models.TextField()
    Submitter_ClinVar = models.TextField()
    SCV_ClinVar = models.TextField()
    Allele_Origin_ClinVar = models.TextField()
    Method_ClinVar = models.TextField()
    Functional_analysis_result_LOVD = models.TextField()
    Functional_analysis_technique_LOVD = models.TextField()
    Variant_frequency_LOVD = models.TextField()
    Variant_haplotype_LOVD = models.TextField()
    HGVS_cDNA_LOVD = models.TextField()
    HGVS_protein_LOVD = models.TextField()
    Individuals_LOVD = models.TextField()
    Variant_effect_LOVD = models.TextField()
    Genetic_origin_LOVD = models.TextField()
    RNA_LOVD = models.TextField()
    Submitters_LOVD = models.TextField()
    Created_date_LOVD = models.TextField(default="-")
    Edited_date_LOVD = models.TextField(default="-")
    DBID_LOVD = models.TextField(default='-')
    Minor_allele_frequency_percent_ESP = models.TextField()
    EA_Allele_Frequency_ESP = models.TextField(default='-')
    AA_Allele_Frequency_ESP = models.TextField(default='-')
    Allele_Frequency_ESP = models.TextField(default='-')
    EUR_Allele_frequency_1000_Genomes = models.TextField()
    AFR_Allele_frequency_1000_Genomes = models.TextField()
    AMR_Allele_frequency_1000_Genomes = models.TextField()
    EAS_Allele_frequency_1000_Genomes = models.TextField()
    Allele_frequency_1000_Genomes = models.TextField()
    SAS_Allele_frequency_1000_Genomes = models.TextField()
    Allele_frequency_ExAC = models.TextField()
    Allele_count_AFR_ExAC = models.TextField(default="-")
    Allele_number_AFR_ExAC = models.TextField(default="-")
    Allele_frequency_AFR_ExAC = models.TextField(default="-")
    Homozygous_count_AFR_ExAC = models.TextField(default="-")
    Allele_count_AMR_ExAC = models.TextField(default="-")
    Allele_number_AMR_ExAC = models.TextField(default="-")
    Allele_frequency_AMR_ExAC = models.TextField(default="-")
    Homozygous_count_AMR_ExAC = models.TextField(default="-")
    Allele_count_EAS_ExAC = models.TextField(default="-")
    Allele_number_EAS_ExAC = models.TextField(default="-")
    Allele_frequency_EAS_ExAC = models.TextField(default="-")
    Homozygous_count_EAS_ExAC = models.TextField(default="-")
    Allele_count_FIN_ExAC = models.TextField(default="-")
    Allele_number_FIN_ExAC = models.TextField(default="-")
    Allele_frequency_FIN_ExAC = models.TextField(default="-")
    Homozygous_count_FIN_ExAC = models.TextField(default="-")
    Allele_count_NFE_ExAC = models.TextField(default="-")
    Allele_number_NFE_ExAC = models.TextField(default="-")
    Allele_frequency_NFE_ExAC = models.TextField(default="-")
    Homozygous_count_NFE_ExAC = models.TextField(default="-")
    Allele_count_OTH_ExAC = models.TextField(default="-")
    Allele_number_OTH_ExAC = models.TextField(default="-")
    Allele_frequency_OTH_ExAC = models.TextField(default="-")
    Homozygous_count_OTH_ExAC = models.TextField(default="-")
    Allele_count_SAS_ExAC = models.TextField(default="-")
    Allele_number_SAS_ExAC = models.TextField(default="-")
    Allele_frequency_SAS_ExAC = models.TextField(default="-")
    Homozygous_count_SAS_ExAC = models.TextField(default="-")
    Patient_nationality_BIC = models.TextField()
    Clinical_importance_BIC = models.TextField()
    Clinical_classification_BIC = models.TextField()
    Literature_citation_BIC = models.TextField()
    Number_of_family_member_carrying_mutation_BIC = models.TextField()
    Germline_or_Somatic_BIC = models.TextField()
    Ethnicity_BIC = models.TextField()
    Mutation_type_BIC = models.TextField()
    IARC_class_exLOVD = models.TextField()
    Sum_family_LR_exLOVD = models.TextField()
    Combined_prior_probablility_exLOVD = models.TextField()
    Literature_source_exLOVD = models.TextField()
    Co_occurrence_LR_exLOVD = models.TextField()
    Posterior_probability_exLOVD = models.TextField()
    Missense_analysis_prior_probability_exLOVD = models.TextField()
    Segregation_LR_exLOVD = models.TextField()
    Gene_Symbol = models.TextField()
    Reference_Sequence = models.TextField()
    HGVS_cDNA = models.TextField()
    BIC_Nomenclature = models.TextField()
    HGVS_Protein = models.TextField()
    HGVS_RNA = models.TextField()
    Protein_Change = models.TextField()
    Allele_Frequency = models.TextField()
    Max_Allele_Frequency = models.TextField()
    Genomic_Coordinate_hg38 = models.TextField()
    Hg38_Start = models.BigIntegerField(default=1)
    Hg38_End = models.BigIntegerField(default=1)
    Hg37_Start = models.BigIntegerField(default=1)
    Hg37_End = models.BigIntegerField(default=1)
    Hg36_Start = models.BigIntegerField(default=1)
    Hg36_End = models.BigIntegerField(default=1)
    Genomic_Coordinate_hg37 = models.TextField()
    Genomic_Coordinate_hg36 = models.TextField()
    Source_URL = models.TextField()
    Discordant = models.TextField()
    Synonyms = models.TextField()
    Pathogenicity_expert = models.TextField()
    Pathogenicity_all = models.TextField()
    Chr = models.TextField()
    Pos = models.TextField()
    Ref = models.TextField()
    Alt = models.TextField()
    Polyphen_Prediction = models.TextField()
    Polyphen_Score = models.TextField()
    Sift_Score = models.TextField()
    Sift_Prediction = models.TextField()
    BX_ID_ENIGMA = models.TextField(default='')
    BX_ID_LOVD = models.TextField(default='')
    BX_ID_ESP = models.TextField(default='')
    BX_ID_BIC = models.TextField(default='')
    BX_ID_ClinVar = models.TextField(default='')
    BX_ID_1000_Genomes = models.TextField(default='')
    BX_ID_ExAC = models.TextField(default='')
    BX_ID_exLOVD = models.TextField(default='')

    # Data Versioning
    Data_Release = models.ForeignKey(DataRelease)
    Change_Type = models.ForeignKey(ChangeType)

    class Meta:
        db_table = 'currentvariant'
        managed = False
