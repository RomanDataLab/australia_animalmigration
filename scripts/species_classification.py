"""
Species classification by group (mammals, birds, amphibians).

This module provides classification functions for organizing species
into groups for visualization.
"""

# Species classification dictionary
SPECIES_GROUPS = {
    # Mammals (10 species)
    'Macropus giganteus': 'mammals',
    'Phascolarctos cinereus': 'mammals',
    'Tachyglossus aculeatus': 'mammals',
    'Macropus rufus': 'mammals',
    'Vombatus ursinus': 'mammals',
    'Trichosurus vulpecula': 'mammals',
    'Isoodon obesulus': 'mammals',
    'Perameles nasuta': 'mammals',
    'Wallabia bicolor': 'mammals',
    'Pseudocheirus peregrinus': 'mammals',
    
    # Birds (10 species)
    'Dromaius novaehollandiae': 'birds',
    'Cacatua galerita': 'birds',
    'Gymnorhina tibicen': 'birds',
    'Platycercus eximius': 'birds',
    'Corvus coronoides': 'birds',
    'Acanthiza pusilla': 'birds',
    'Meliphaga lewinii': 'birds',
    'Pardalotus punctatus': 'birds',
    'Rhipidura leucophrys': 'birds',
    'Eolophus roseicapilla': 'birds',
    
    # Amphibians (10 species)
    'Litoria caerulea': 'amphibians',
    'Limnodynastes dumerilii': 'amphibians',
    'Crinia signifera': 'amphibians',
    'Litoria peronii': 'amphibians',
    'Limnodynastes tasmaniensis': 'amphibians',
    'Litoria ewingii': 'amphibians',
    'Uperoleia laevigata': 'amphibians',
    'Litoria raniformis': 'amphibians',
    'Pseudophryne bibronii': 'amphibians',
    'Litoria verreauxii': 'amphibians',
}

def get_species_group(species_name):
    """
    Get the group (mammals, birds, amphibians) for a species.
    
    Parameters:
    -----------
    species_name : str
        Scientific name of the species
        
    Returns:
    --------
    str or None
        Group name ('mammals', 'birds', 'amphibians') or None if not found
    """
    # Try exact match first
    if species_name in SPECIES_GROUPS:
        return SPECIES_GROUPS[species_name]
    
    # Try with underscores replaced by spaces
    species_normalized = species_name.replace('_', ' ')
    if species_normalized in SPECIES_GROUPS:
        return SPECIES_GROUPS[species_normalized]
    
    # Try case-insensitive match
    for key, value in SPECIES_GROUPS.items():
        if key.lower() == species_name.lower() or key.lower() == species_normalized.lower():
            return value
    
    return None

def get_all_species_by_group():
    """
    Get all species organized by group.
    
    Returns:
    --------
    dict
        Dictionary mapping group names to lists of species names
    """
    groups = {
        'mammals': [],
        'birds': [],
        'amphibians': []
    }
    
    for species, group in SPECIES_GROUPS.items():
        groups[group].append(species)
    
    return groups

def classify_species_file(species_file):
    """
    Classify a species file by its name.
    
    Parameters:
    -----------
    species_file : Path
        Path to species JSON file
        
    Returns:
    --------
    str or None
        Group name or None if not found
    """
    species_name = species_file.stem.replace('_', ' ')
    return get_species_group(species_name)

