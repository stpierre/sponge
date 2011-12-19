%if 0%{?rhel} <= 5
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

Summary: Web interface to Pulp
Name: sponge
Version: 0.1.2
Release: 1
License: Other non-free
Group: System Tools
URL: http://www.nccs.gov
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

BuildRequires: python
Requires: mod_wsgi

%description
Sponge is a web interface to Pulp that enforces a particular
promote/demote workflow.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}
cp -R %{name}.wsgi media %{buildroot}%{_datadir}/%{name}

%{__mkdir_p} %{buildroot}%{python_sitelib}
cp -R Sponge %{buildroot}%{python_sitelib}

%{__mkdir_p} %{buildroot}%{_defaultdocdir}/%{name}-%{version}
cp README* %{buildroot}%{_defaultdocdir}/%{name}-%{version}

%{__mkdir_p} %{buildroot}%{_sharedstatedir}/%{name}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_datadir}/%{name}
%{python_sitelib}/Sponge
%attr(750,apache,apache) %{_sharedstatedir}/%{name}

%doc %{_defaultdocdir}/%{name}-%{version}

%config %{python_sitelib}/Sponge/settings.py

%changelog
* Wed Dec 14 2011 Chris St. Pierre <stpierreca@ornl.gov> 0.1.1-1
- Added docs

* Tue Nov 15 2011 Chris St. Pierre <stpierreca@ornl.gov> 
- Initial build.


