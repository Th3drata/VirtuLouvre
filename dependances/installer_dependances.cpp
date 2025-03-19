#include <iostream>
#include <cstdlib>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <windows.h> // Pour la gestion des accents sous Windows

#ifdef _WIN32
    #define PYTHON_CMD "python"
    #define PIP_CMD "pip"
#else
    #define PYTHON_CMD "python3"
    #define PIP_CMD "pip3"
#endif

// Configuration des accents pour Windows
void configurerAccents() {
    #ifdef _WIN32
        SetConsoleOutputCP(CP_UTF8);
        SetConsoleCP(CP_UTF8);
    #endif
}

// Vérifier l'installation de Python
bool verifierInstallationPython() {
    std::string cmd = std::string(PYTHON_CMD) + " --version";
    return system(cmd.c_str()) == 0;
}

// Vérifier l'installation de pip
bool verifierInstallationPip() {
    std::string cmd = std::string(PIP_CMD) + " --version";
    return system(cmd.c_str()) == 0;
}

// Installer les dépendances
bool installerDependances() {
    std::cout << "Installation des dépendances en cours...\n";
    std::string cmd = std::string(PIP_CMD) + " install -r requirements.txt";
    return system(cmd.c_str()) == 0;
}

int main() {
    // Configurer l'affichage des accents
    configurerAccents();

    std::cout << "Vérification de l'installation de Python...\n";
    if (!verifierInstallationPython()) {
        std::cerr << "Erreur : Python n'est pas installé ou n'est pas dans le PATH\n";
        return 1;
    }
    std::cout << "Python est installé\n";

    std::cout << "Vérification de l'installation de pip...\n";
    if (!verifierInstallationPip()) {
        std::cerr << "Erreur : pip n'est pas installé ou n'est pas dans le PATH\n";
        return 1;
    }
    std::cout << "pip est installé\n";

    std::cout << "Installation des dépendances depuis requirements.txt...\n";
    if (!installerDependances()) {
        std::cerr << "Erreur : Échec de l'installation des dépendances\n";
        return 1;
    }
    std::cout << "Dépendances installées avec succès !\n";

    return 0;
} 