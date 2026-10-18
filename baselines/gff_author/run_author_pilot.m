% Wrapper only. Author files in author/ are not edited.
function run_author_pilot(root)
  if exist('OCTAVE_VERSION','builtin')
    pkg load image;
  end
  addpath(fullfile(root,'author'));
  fp=fopen(fullfile(root,'pilot','cases.tsv'),'r');
  cleanup=onCleanup(@() fclose(fp));
  data=textscan(fp,'%s%s%s%s','Delimiter','\t');
  logfp=fopen(fullfile(root,'pilot','author_runtime.tsv'),'a');
  cleanup2=onCleanup(@() fclose(logfp));
  for k=1:numel(data{1})
    target=data{4}{k};
    if exist(target,'file'), continue; end
    A=imread(data{2}{k});B=imread(data{3}{k});
    assert(isa(A,'uint8') && isa(B,'uint8'));
    assert(isequal(size(A),size(B)));
    I=cat(4,A,B);
    tic;F=GFF(I);seconds=toc;
    assert(isa(F,'uint8') && isequal(size(F),size(A)));
    imwrite(F,target);
    fprintf(logfp,'%s\t%.9f\n',data{1}{k},seconds);if exist('OCTAVE_VERSION','builtin'), fflush(logfp); end
    fprintf('%s complete %.6f seconds\n',data{1}{k},seconds);
  end
end
