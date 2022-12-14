from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir, save, rename
from conan.tools.microsoft import is_msvc
from os import environ
import os
import textwrap

required_conan_version = ">=1.50.0"

def determine_git_url():
    try:
        if environ['CONAN_HTTPS_USERNAME'] is not None:
            remote_url = "https://github.com/dyndrite/g3log.git"
            return remote_url
    except KeyError:
        return "git@github.com:dyndrite/g3log.git"


def determine_https_user():
    try:
        if environ['CONAN_HTTPS_USERNAME'] is not None:
            http_user = environ['CONAN_HTTPS_USERNAME']
            return http_user
    except KeyError:
        return None

def determine_https_pass():
    try:
        if environ['CONAN_HTTPS_PASS'] is not None:
            http_pass = environ['CONAN_HTTPS_PASS']
            return http_pass
    except KeyError:
        return None

class G3logConan(ConanFile):
    name = "dynd-g3log"
    revision_mode = "scm"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/KjellKod/g3log"
    license = "The Unlicense"
    description = (
        "G3log is an asynchronous, \"crash safe\", logger that is easy to use "
        "with default logging sinks or you can add your own."
    )
    topics = ("g3log", "log")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_dynamic_logging_levels": [True, False],
        "change_debug_to_dbug": [True, False],
        "use_dynamic_max_message_size": [True, False],
        "log_full_filename": [True, False],
        "enable_fatal_signal_handling": [True, False],
        "enable_vectored_exception_handling": [True, False],
        "debug_break_at_fatal_signal": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_dynamic_logging_levels": True,
        "change_debug_to_dbug": True,
        "use_dynamic_max_message_size": True,
        "log_full_filename": False,
        "enable_fatal_signal_handling": False,
        "enable_vectored_exception_handling": False,
        "debug_break_at_fatal_signal": False,
    }	

    scm = {
        "type": "git",
        "url": determine_git_url(),
        "revision": "auto",
        "username": determine_https_user(),
        "password": determine_https_pass()
    }

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "6.1",
            "clang": "3.4",
            "apple-clang": "5.1",
            "Visual Studio": "15",
        }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_msvc(self):
            del self.options.enable_vectored_exception_handling
            del self.options.debug_break_at_fatal_signal

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.info.settings.compiler.cppstd:
            check_min_cppstd(self, "14")

        def loose_lt_semver(v1, v2):
            lv1 = [int(v) for v in v1.split(".")]
            lv2 = [int(v) for v in v2.split(".")]
            min_length = min(len(lv1), len(lv2))
            return lv1[:min_length] < lv2[:min_length]

        minimum_version = self._compilers_minimum_version.get(str(self.info.settings.compiler), False)
        if minimum_version and loose_lt_semver(str(self.info.settings.compiler.version), minimum_version):
            raise ConanInvalidConfiguration(
                "{} requires C++14, which your compiler does not support.".format(self.name)
            )

    def layout(self):
        cmake_layout(self, src_folder=self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VERSION"] = self.version
        tc.variables["G3_SHARED_LIB"] = self.options.shared
        tc.variables["USE_DYNAMIC_LOGGING_LEVELS"] = self.options.use_dynamic_logging_levels
        tc.variables["CHANGE_G3LOG_DEBUG_TO_DBUG"] = self.options.change_debug_to_dbug
        tc.variables["USE_G3_DYNAMIC_MAX_MESSAGE_SIZE"] = self.options.use_dynamic_max_message_size
        tc.variables["G3_LOG_FULL_FILENAME"] = self.options.log_full_filename
        tc.variables["ENABLE_FATAL_SIGNALHANDLING"] = self.options.enable_fatal_signal_handling
        if is_msvc(self):
            tc.variables["ENABLE_VECTORED_EXCEPTIONHANDLING"] = self.options.enable_vectored_exception_handling
            tc.variables["DEBUG_BREAK_AT_FATAL_SIGNAL"] = self.options.debug_break_at_fatal_signal
        tc.variables["ADD_FATAL_EXAMPLE"] = "OFF"
        tc.variables["ADD_G3LOG_PERFORMANCE"] = "OFF"
        tc.variables["ADD_G3LOG_UNIT_TEST"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._module_file_rel_path),
            {"g3log": "g3log::g3log"},
        )
        self._rename_libraries()

    def _create_cmake_module_alias_targets(self, module_file, targets):
        content = ""
        for alias, aliased in targets.items():
            content += textwrap.dedent(f"""\
                if(TARGET {aliased} AND NOT TARGET {alias})
                    add_library({alias} INTERFACE IMPORTED)
                    set_property(TARGET {alias} PROPERTY INTERFACE_LINK_LIBRARIES {aliased})
                endif()
            """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-targets.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "g3logger")
        self.cpp_info.set_property("cmake_target_name", "g3logger")
        self.cpp_info.libs = ["g3logger"]
        self.cpp_info.names["cmake_find_package"] = "g3logger"
        self.cpp_info.names["cmake_find_package_multi"] = "g3logger"

        if str(self.settings.os) in ["Linux", "Android"]:
            self.cpp_info.libs.append('pthread')
        self.cpp_info.build_modules["cmake_find_package"] = [self._module_file_rel_path]
        self.cpp_info.build_modules["cmake_find_package_multi"] = [self._module_file_rel_path]

    def _rename_libraries(self):
        if self.settings.os == "Windows":
            lib_path = os.path.join(self.package_folder, "lib")
            if self.options.shared:
                if self.settings.compiler == "Visual Studio":
                    current_lib = os.path.join(lib_path, "g3log.lib")
                    rename(self, src=current_lib, dst=os.path.join(lib_path, "g3logger.lib"))
            else:
                if self.settings.compiler == "Visual Studio":
                    current_lib = os.path.join(lib_path, "g3log.lib")
                    rename(self, src=current_lib, dst=os.path.join(lib_path, "g3logger.lib"))
                elif self.settings.compiler == "gcc":
                    current_lib = os.path.join(lib_path, "libg3log.a")
                    rename(self, src=current_lib, dst=os.path.join(lib_path, "libg3logger.a"))
                elif self.settings.compiler == "clang":
                    current_lib = os.path.join(lib_path, "g3log.lib")
                    rename(self, src=current_lib, dst=os.path.join(lib_path, "g3logger.lib"))
        if self.settings.os == "Linux":
            lib_path = os.path.join(self.package_folder, "lib")
            if self.settings.compiler == "gcc":
                current_lib = os.path.join(lib_path, "libg3log.a")
                rename(self, src=current_lib, dst=os.path.join(lib_path, "libg3logger.a"))
            elif self.settings.compiler == "clang":
                current_lib = os.path.join(lib_path, "libg3log.a")
                rename(self, src=current_lib, dst=os.path.join(lib_path, "libg3logger.a"))
