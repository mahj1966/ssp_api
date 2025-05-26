"""Modèles de données pour les ressources cloud."""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class SecurityGroupRule:
    """Représente une règle de groupe de sécurité."""
    request_id: int
    from_port: int
    to_port: int
    protocol: str
    cidr: str
    id: Optional[int] = None
    description: Optional[str] = None


@dataclass
class CloudResource:
    """Classe de base pour toutes les ressources cloud."""
    id: int
    name: str
    cloud_id: str
    resource_type: str
    module_version: str
    gitlab_project_id: int
    created_by: str
    created_at: str
    sg_rules: List[SecurityGroupRule] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Crée une instance de la ressource à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la ressource
            
        Returns:
            Instance de CloudResource
        """
        sg_rules = []
        if 'sg_rules' in data:
            sg_rules = [
                SecurityGroupRule(
                    request_id=rule.get('request_id'),
                    from_port=rule.get('from_port'),
                    to_port=rule.get('to_port'),
                    protocol=rule.get('protocol'),
                    cidr=rule.get('cidr'),
                    id=rule.get('id'),
                    description=rule.get('description')
                )
                for rule in data['sg_rules']
            ]
            del data['sg_rules']
        
        # Extraire les attributs de base
        base_attrs = {
            'id': data.pop('id', None),
            'name': data.pop('name', None),
            'cloud_id': data.pop('cloud_id', None),
            'resource_type': data.pop('resource_type', None),
            'module_version': data.pop('module_version', None),
            'gitlab_project_id': data.pop('gitlab_project_id', None),
            'created_by': data.pop('created_by', None),
            'created_at': data.pop('created_at', None),
            'sg_rules': sg_rules,
            'attributes': data  # Le reste des données devient des attributs
        }
        
        return cls(**base_attrs)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant la ressource
        """
        result = {
            'id': self.id,
            'name': self.name,
            'cloud_id': self.cloud_id,
            'resource_type': self.resource_type,
            'module_version': self.module_version,
            'gitlab_project_id': self.gitlab_project_id,
            'created_by': self.created_by,
            'created_at': self.created_at,
        }
        
        # Ajouter les règles SG si elles existent
        if self.sg_rules:
            result['sg_rules'] = [
                {
                    'request_id': rule.request_id,
                    'from_port': rule.from_port,
                    'to_port': rule.to_port,
                    'protocol': rule.protocol,
                    'cidr': rule.cidr,
                    'description': rule.description
                } 
                for rule in self.sg_rules
            ]
        
        # Ajouter tous les attributs spécifiques
        result.update(self.attributes)
        
        return result


@dataclass
class AwsRdsResource(CloudResource):
    """Représente une ressource AWS RDS."""
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    instance_class: Optional[str] = None
    allocated_storage: Optional[int] = None
    storage_type: Optional[str] = None
    multi_az: Optional[bool] = False
    publicly_accessible: Optional[bool] = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Crée une instance de ressource AWS RDS à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la ressource
            
        Returns:
            Instance de AwsRdsResource
        """
        # Extraire les attributs spécifiques à RDS
        rds_attrs = {
            'engine': data.pop('engine', None),
            'engine_version': data.pop('engine_version', None),
            'instance_class': data.pop('instance_class', None),
            'allocated_storage': data.pop('allocated_storage', None),
            'storage_type': data.pop('storage_type', None),
            'multi_az': data.pop('multi_az', False),
            'publicly_accessible': data.pop('publicly_accessible', False),
        }
        
        # Créer une instance de base
        instance = super().from_dict(data)
        
        # Ajouter les attributs spécifiques
        for key, value in rds_attrs.items():
            setattr(instance, key, value)
            
        return instance


@dataclass
class AwsEc2Resource(CloudResource):
    """Représente une ressource AWS EC2."""
    instance_type: Optional[str] = None
    ami_id: Optional[str] = None
    key_name: Optional[str] = None
    subnet_id: Optional[str] = None
    vpc_security_group_ids: Optional[List[str]] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Crée une instance de ressource AWS EC2 à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la ressource
            
        Returns:
            Instance de AwsEc2Resource
        """
        # Extraire les attributs spécifiques à EC2
        ec2_attrs = {
            'instance_type': data.pop('instance_type', None),
            'ami_id': data.pop('ami_id', None),
            'key_name': data.pop('key_name', None),
            'subnet_id': data.pop('subnet_id', None),
            'vpc_security_group_ids': data.pop('vpc_security_group_ids', []),
        }
        
        # Créer une instance de base
        instance = super().from_dict(data)
        
        # Ajouter les attributs spécifiques
        for key, value in ec2_attrs.items():
            setattr(instance, key, value)
            
        return instance


# Vous pouvez ajouter des classes pour d'autres types de ressources
@dataclass
class GcpCloudSqlResource(CloudResource):
    """Représente une ressource Google Cloud SQL."""
    database_version: Optional[str] = None
    tier: Optional[str] = None
    disk_size: Optional[int] = None
    region: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Crée une instance GCP Cloud SQL à partir d'un dictionnaire."""
        # Attributs spécifiques à Cloud SQL
        sql_attrs = {
            'database_version': data.pop('database_version', None),
            'tier': data.pop('tier', None),
            'disk_size': data.pop('disk_size', None),
            'region': data.pop('region', None),
        }
        
        instance = super().from_dict(data)
        
        for key, value in sql_attrs.items():
            setattr(instance, key, value)
            
        return instance


# Factory pour créer des instances de ressources en fonction du type
def create_resource(data: Dict[str, Any]) -> CloudResource:
    """
    Crée une instance de ressource appropriée en fonction du type de ressource et du cloud.
    
    Args:
        data: Dictionnaire contenant les données de la ressource
        
    Returns:
        Instance de CloudResource ou d'une classe dérivée
    """
    cloud_id = data.get('cloud_id', '').lower()
    resource_type = data.get('resource_type', '').lower()
    
    if cloud_id == 'aws':
        if resource_type == 'rds':
            return AwsRdsResource.from_dict(data)
        elif resource_type == 'ec2':
            return AwsEc2Resource.from_dict(data)
    elif cloud_id == 'gcp':
        if resource_type == 'cloudsql':
            return GcpCloudSqlResource.from_dict(data)
    
    # Par défaut, retourner une ressource cloud générique
    return CloudResource.from_dict(data)
